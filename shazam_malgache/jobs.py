"""
Pipeline d'ingestion asynchrone (file d'attente + suivi de progression).

Un « job » décrit l'ingestion d'un morceau, depuis une URL (YouTube via yt-dlp)
ou un fichier uploadé. Le travail est lourd (téléchargement + décodage + calcul
d'empreinte) : il tourne donc dans un pool de threads en arrière-plan, et son
avancement est persisté en base pour que l'interface de gestion l'affiche en
temps réel.

Règle d'or INCHANGÉE : l'audio n'existe que transitoirement (fichier temporaire
supprimé, échantillons jetés). Seules les empreintes irréversibles sont gardées.

Étapes d'un job :
    queued -> metadata -> download -> decode -> fingerprint -> store -> done
                                                              (ou -> error)
"""
from __future__ import annotations

import os
import sqlite3
import tempfile
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from shazam_malgache import audio_io, db
from shazam_malgache.fingerprint import fingerprint

JOBS_SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    id           TEXT PRIMARY KEY,
    kind         TEXT NOT NULL,          -- 'url' | 'file'
    url          TEXT,
    title        TEXT,
    artist       TEXT,
    status       TEXT NOT NULL,          -- queued|running|done|error
    stage        TEXT,                   -- metadata|download|decode|fingerprint|store|done
    progress     REAL NOT NULL DEFAULT 0,
    message      TEXT,
    song_id      INTEGER,
    fingerprints INTEGER,
    error        TEXT,
    created_at   TEXT NOT NULL,
    updated_at   TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_jobs_created ON jobs(created_at);
"""

# Étapes -> avancement de référence (la phase download affine entre 0.10 et 0.60).
STAGE_PROGRESS = {
    "queued": 0.0,
    "metadata": 0.05,
    "download": 0.10,
    "decode": 0.70,
    "fingerprint": 0.85,
    "store": 0.95,
    "done": 1.0,
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _db_path() -> str:
    return os.environ.get("SHAZAM_DB", "shazam.db")


# --- Pool de workers --------------------------------------------------------
_executor = ThreadPoolExecutor(
    max_workers=int(os.environ.get("SHAZAM_WORKERS", "2")),
    thread_name_prefix="ingest",
)


def ensure_table(conn) -> None:
    """Crée la table des jobs si besoin (idempotent, sans effet de bord)."""
    if db.IS_PG:
        with conn.cursor() as cur:
            cur.execute(JOBS_SCHEMA)  # psycopg2 accepte plusieurs instructions
    else:
        conn.executescript(JOBS_SCHEMA)
        conn.commit()


def init(conn) -> None:
    """À appeler UNE FOIS au démarrage : crée la table puis marque comme
    interrompus les jobs restés 'queued'/'running' d'un process précédent.

    Surtout pas à chaque requête : cela tuerait les jobs réellement en cours."""
    ensure_table(conn)
    db.execute(
        conn,
        "UPDATE jobs SET status='error', error='interrompu (redémarrage du serveur)', "
        "updated_at=? WHERE status IN ('queued','running')",
        (_now(),),
    )


def _row_to_dict(row: tuple, cols: list[str]) -> dict:
    return dict(zip(cols, row))


_COLS = [
    "id", "kind", "url", "title", "artist", "status", "stage", "progress",
    "message", "song_id", "fingerprints", "error", "created_at", "updated_at",
]


def list_jobs(conn, limit: int = 50) -> list[dict]:
    rows = db.q(
        conn,
        f"SELECT {','.join(_COLS)} FROM jobs ORDER BY created_at DESC LIMIT ?",
        (limit,),
    )
    return [_row_to_dict(r, _COLS) for r in rows]


def get_job(conn, job_id: str) -> dict | None:
    row = db.q1(conn, f"SELECT {','.join(_COLS)} FROM jobs WHERE id = ?", (job_id,))
    return _row_to_dict(row, _COLS) if row else None


def active_count(conn) -> int:
    row = db.q1(conn, "SELECT COUNT(*) FROM jobs WHERE status IN ('queued','running')")
    return int(row[0])


def submit(kind: str, *, url: str = "", title: str = "", artist: str = "",
           file_path: str = "") -> dict:
    """Crée un job, le persiste en 'queued' et le confie au pool de workers."""
    job_id = uuid.uuid4().hex
    now = _now()
    conn = db.connect(_db_path())
    ensure_table(conn)
    db.execute(
        conn,
        "INSERT INTO jobs(id, kind, url, title, artist, status, stage, progress, "
        "message, created_at, updated_at) VALUES (?,?,?,?,?, 'queued','queued',0, "
        "'en attente', ?, ?)",
        (job_id, kind, url, title, artist, now, now),
    )
    job = get_job(conn, job_id)
    conn.close()

    _executor.submit(_run, job_id, file_path)
    return job


# --- Exécution d'un job -----------------------------------------------------

def _update(conn, job_id, **fields) -> None:
    fields["updated_at"] = _now()
    sets = ", ".join(f"{k} = ?" for k in fields)
    db.execute(conn, f"UPDATE jobs SET {sets} WHERE id = ?", (*fields.values(), job_id))


def _set_stage(conn, job_id, stage: str, message: str = "") -> None:
    _update(
        conn, job_id, status="running", stage=stage,
        progress=STAGE_PROGRESS.get(stage, 0.0), message=message or stage,
    )


def _download(url: str, tmpdir: str, on_progress) -> str:
    """Télécharge le meilleur flux audio via l'API yt-dlp, avec progression."""
    import yt_dlp  # import paresseux : n'alourdit pas le démarrage de l'API

    last = {"p": 0.0}

    def hook(d):
        if d.get("status") == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            done = d.get("downloaded_bytes") or 0
            frac = (done / total) if total else 0.0
            # download couvre 0.10 -> 0.60
            p = 0.10 + 0.50 * max(0.0, min(1.0, frac))
            if p - last["p"] >= 0.02:
                last["p"] = p
                pct = int(frac * 100)
                on_progress(p, f"téléchargement {pct}%")

    out_tpl = os.path.join(tmpdir, "audio.%(ext)s")
    opts = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,  # ne récupérer QUE la vidéo, jamais le mix/playlist
        "format": "bestaudio",
        "outtmpl": out_tpl,
        "progress_hooks": [hook],
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([url])

    files = [os.path.join(tmpdir, f) for f in os.listdir(tmpdir)]
    if not files:
        raise RuntimeError(f"yt-dlp n'a rien téléchargé pour {url}")
    return files[0]


def _run(job_id: str, file_path: str = "") -> None:
    """Worker : exécute le pipeline d'un job. L'audio est jeté quoi qu'il arrive."""
    conn = db.connect(_db_path())
    job = get_job(conn, job_id)
    if not job:
        conn.close()
        return

    tmpdir = ""
    audio_path = file_path
    try:
        title = (job["title"] or "").strip()
        artist = (job["artist"] or "").strip()
        source = job["url"] or "file"

        if job["kind"] == "url":
            url = job["url"]
            # 1) métadonnées (sans télécharger l'audio) — complète le titre si vide
            _set_stage(conn, job_id, "metadata", "lecture des métadonnées")
            try:
                meta = audio_io.fetch_metadata(url)
                if not title:
                    title = meta.get("title") or url
                if not artist:
                    artist = meta.get("uploader") or ""
                _update(conn, job_id, title=title, artist=artist)
            except Exception:
                if not title:
                    title = url  # on ingère quand même, titre = URL

            # 2) téléchargement transitoire
            _set_stage(conn, job_id, "download", "téléchargement de l'audio")
            tmpdir = tempfile.mkdtemp(prefix="shz_job_")
            audio_path = _download(
                url, tmpdir,
                lambda p, m: _update(conn, job_id, progress=p, message=m),
            )
        else:
            if not title:
                title = os.path.basename(file_path) or "fichier"

        # 3) décodage (ffmpeg) -> échantillons mono
        _set_stage(conn, job_id, "decode", "décodage de l'audio")
        samples = audio_io.decode_file(audio_path)

        # 4) empreinte (l'audio est jeté juste après)
        _set_stage(conn, job_id, "fingerprint", "calcul de l'empreinte")
        hashes = fingerprint(samples)
        del samples  # <-- audio jeté

        # 5) stockage (métadonnées + empreintes uniquement)
        _set_stage(conn, job_id, "store", "enregistrement des empreintes")
        song_id = db.add_song(conn, title, artist, source)
        n = db.store_fingerprints(conn, song_id, hashes)

        _update(
            conn, job_id, status="done", stage="done", progress=1.0,
            song_id=song_id, fingerprints=n,
            message=f"{n} empreintes enregistrées — audio jeté",
        )
    except Exception as exc:  # noqa: BLE001 — on remonte l'erreur à l'UI
        _update(
            conn, job_id, status="error",
            error=str(exc), message=f"échec : {exc}",
        )
    finally:
        # On jette l'audio quoi qu'il arrive : fichier uploadé + dossier temporaire.
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except OSError:
                pass
        if tmpdir and os.path.isdir(tmpdir):
            for f in os.listdir(tmpdir):
                try:
                    os.remove(os.path.join(tmpdir, f))
                except OSError:
                    pass
            try:
                os.rmdir(tmpdir)
            except OSError:
                pass
        conn.close()
