"""
API d'administration de Shazam Malgache (préfixe /api).

Sert l'interface de gestion Next.js : exploration des catalogues (morceaux
indexés + référentiel d'artistes Moozik), ajout de morceaux et pilotage du
pipeline d'ingestion YouTube (jobs asynchrones avec progression).

Aucun de ces endpoints ne renvoie ni ne stocke d'audio : uniquement des
métadonnées et des empreintes irréversibles.
"""
from __future__ import annotations

import os
import tempfile

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from pydantic import BaseModel

from shazam_malgache import audio_io, catalog, db, jobs

router = APIRouter(prefix="/api")


def _db_path() -> str:
    return os.environ.get("SHAZAM_DB", "shazam.db")


def _conn():
    conn = db.connect(_db_path())
    jobs.ensure_table(conn)  # idempotent ; le nettoyage des jobs interrompus se fait au démarrage
    return conn


# --- Statistiques -----------------------------------------------------------

@router.get("/stats")
def get_stats() -> dict:
    conn = _conn()
    engine = db.stats(conn)
    active = jobs.active_count(conn)
    conn.close()
    return {"engine": engine, "catalog": catalog.stats(), "jobs_active": active}


# --- Morceaux indexés (catalogue d'empreintes) ------------------------------

@router.get("/songs")
def get_songs(
    q: str = "",
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> dict:
    conn = _conn()
    total = db.count_songs(conn, q)
    songs = db.list_songs(conn, q, limit, offset)
    conn.close()
    return {"total": total, "songs": songs}


@router.get("/songs/{song_id}")
def get_song(song_id: int) -> dict:
    conn = _conn()
    song = db.song_detail(conn, song_id)
    conn.close()
    if not song:
        raise HTTPException(status_code=404, detail="morceau introuvable")
    return song


class SongPatch(BaseModel):
    title: str
    artist: str = ""


@router.patch("/songs/{song_id}")
def patch_song(song_id: int, body: SongPatch) -> dict:
    conn = _conn()
    if not db.get_song(conn, song_id):
        conn.close()
        raise HTTPException(status_code=404, detail="morceau introuvable")
    song = db.update_song(conn, song_id, body.title.strip(), body.artist.strip())
    conn.close()
    return song


@router.delete("/songs/{song_id}")
def remove_song(song_id: int) -> dict:
    conn = _conn()
    ok = db.delete_song(conn, song_id)
    conn.close()
    if not ok:
        raise HTTPException(status_code=404, detail="morceau introuvable")
    return {"deleted": True, "id": song_id}


# --- Référentiel d'artistes (catalogue Moozik) ------------------------------

@router.get("/catalog/artists")
def get_catalog_artists(
    q: str = "",
    sort: str = Query("rank", pattern="^(rank|name|plays|tracks)$"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> dict:
    return catalog.list_artists(q, sort, limit, offset)


# --- Sondage YouTube (métadonnées sans téléchargement) ----------------------

class ProbeBody(BaseModel):
    url: str


@router.post("/youtube/probe")
def probe_youtube(body: ProbeBody) -> dict:
    url = body.url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="URL vide")
    try:
        return audio_io.fetch_metadata(url)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"URL illisible : {exc}") from exc


# --- Pipeline d'ingestion (jobs) --------------------------------------------

class IngestBody(BaseModel):
    url: str
    title: str = ""
    artist: str = ""


@router.post("/jobs", status_code=202)
def create_ingest_job(body: IngestBody) -> dict:
    url = body.url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="URL vide")
    return jobs.submit("url", url=url, title=body.title.strip(), artist=body.artist.strip())


class BatchBody(BaseModel):
    urls: list[str]
    artist: str = ""


@router.post("/jobs/batch", status_code=202)
def create_batch_jobs(body: BatchBody) -> dict:
    urls = [u.strip() for u in body.urls if u.strip()]
    if not urls:
        raise HTTPException(status_code=400, detail="aucune URL fournie")
    created = [jobs.submit("url", url=u, artist=body.artist.strip()) for u in urls]
    return {"count": len(created), "jobs": created}


@router.post("/jobs/file", status_code=202)
async def create_file_job(
    file: UploadFile = File(...),
    title: str = Form(""),
    artist: str = Form(""),
) -> dict:
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="fichier audio vide")
    # On dépose l'upload dans un fichier temporaire ; le worker le décode puis le
    # supprime (audio jeté). Rien n'est conservé sur disque au-delà du calcul.
    suffix = os.path.splitext(file.filename or "")[1] or ".bin"
    tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False, prefix="shz_up_")
    tmp.write(data)
    tmp.close()
    return jobs.submit(
        "file",
        title=(title or file.filename or "").strip(),
        artist=artist.strip(),
        file_path=tmp.name,
    )


@router.get("/jobs")
def get_jobs(limit: int = Query(50, ge=1, le=200)) -> dict:
    conn = _conn()
    items = jobs.list_jobs(conn, limit)
    conn.close()
    return {"jobs": items}


@router.get("/jobs/{job_id}")
def get_job(job_id: str) -> dict:
    conn = _conn()
    job = jobs.get_job(conn, job_id)
    conn.close()
    if not job:
        raise HTTPException(status_code=404, detail="job introuvable")
    return job
