"""
Stockage persistant des empreintes (SQLite).

On ne stocke QUE des métadonnées (titre/artiste) et des empreintes (hashes
irréversibles). Jamais d'audio. L'interface est volontairement minimale pour
pouvoir basculer plus tard vers Postgres sans toucher au reste du code.
"""
from __future__ import annotations

import sqlite3
from typing import Iterable

from shazam_malgache.fingerprint import LookupFn, match

SCHEMA = """
CREATE TABLE IF NOT EXISTS songs (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    title   TEXT NOT NULL,
    artist  TEXT,
    source  TEXT,                      -- d'où vient le morceau (info, pas l'audio)
    UNIQUE(title, artist)
);
CREATE TABLE IF NOT EXISTS fingerprints (
    hash    INTEGER NOT NULL,
    song_id INTEGER NOT NULL REFERENCES songs(id) ON DELETE CASCADE,
    offset  INTEGER NOT NULL           -- position temporelle (frames) de l'ancre
);
CREATE INDEX IF NOT EXISTS idx_fp_hash ON fingerprints(hash);
"""


def connect(path: str = "shazam.db") -> sqlite3.Connection:
    conn = sqlite3.connect(path, timeout=30.0)
    conn.execute("PRAGMA foreign_keys = ON")
    # Plusieurs workers d'ingestion peuvent écrire en parallèle : on patiente
    # plutôt que d'échouer immédiatement sur un verrou.
    conn.execute("PRAGMA busy_timeout = 30000")
    conn.executescript(SCHEMA)
    return conn


def add_song(conn: sqlite3.Connection, title: str, artist: str = "", source: str = "") -> int:
    cur = conn.execute(
        "INSERT OR IGNORE INTO songs(title, artist, source) VALUES (?, ?, ?)",
        (title, artist, source),
    )
    if cur.lastrowid and cur.rowcount:
        conn.commit()
        return cur.lastrowid
    # déjà présent : on récupère l'id existant
    row = conn.execute(
        "SELECT id FROM songs WHERE title = ? AND artist = ?", (title, artist)
    ).fetchone()
    return int(row[0])


def store_fingerprints(
    conn: sqlite3.Connection, song_id: int, hashes: Iterable[tuple[int, int]]
) -> int:
    rows = [(h, song_id, offset) for h, offset in hashes]
    conn.executemany(
        "INSERT INTO fingerprints(hash, song_id, offset) VALUES (?, ?, ?)", rows
    )
    conn.commit()
    return len(rows)


def make_lookup(conn: sqlite3.Connection) -> LookupFn:
    """Renvoie une fonction hash -> [(song_id, offset), ...] branchée sur SQLite."""

    def lookup(h: int):
        return conn.execute(
            "SELECT song_id, offset FROM fingerprints WHERE hash = ?", (h,)
        ).fetchall()

    return lookup


def get_song(conn: sqlite3.Connection, song_id: int) -> dict | None:
    row = conn.execute(
        "SELECT id, title, artist, source FROM songs WHERE id = ?", (song_id,)
    ).fetchone()
    if not row:
        return None
    return {"id": row[0], "title": row[1], "artist": row[2], "source": row[3]}


def recognize(conn: sqlite3.Connection, query_hashes: list[tuple[int, int]], top_k: int = 5):
    """Reconnaît un extrait et renvoie les meilleurs candidats enrichis des métadonnées."""
    results = match(query_hashes, make_lookup(conn))[:top_k]
    for r in results:
        r["song"] = get_song(conn, r["song_id"])
    return results


# --- Administration / gestion ----------------------------------------------
# Fonctions de lecture/écriture utilisées par l'interface de gestion. Elles ne
# touchent JAMAIS à de l'audio : uniquement métadonnées et compteurs d'empreintes.


def list_songs(
    conn: sqlite3.Connection, q: str = "", limit: int = 50, offset: int = 0
) -> list[dict]:
    """Liste les morceaux indexés avec leur nombre d'empreintes (recherche optionnelle)."""
    where, params = "", []
    if q:
        where = "WHERE s.title LIKE ? OR s.artist LIKE ?"
        params = [f"%{q}%", f"%{q}%"]
    rows = conn.execute(
        f"""
        SELECT s.id, s.title, s.artist, s.source, COUNT(f.hash) AS fp
        FROM songs s
        LEFT JOIN fingerprints f ON f.song_id = s.id
        {where}
        GROUP BY s.id
        ORDER BY s.id DESC
        LIMIT ? OFFSET ?
        """,
        [*params, limit, offset],
    ).fetchall()
    return [
        {"id": r[0], "title": r[1], "artist": r[2], "source": r[3], "fingerprints": r[4]}
        for r in rows
    ]


def count_songs(conn: sqlite3.Connection, q: str = "") -> int:
    if q:
        return int(
            conn.execute(
                "SELECT COUNT(*) FROM songs WHERE title LIKE ? OR artist LIKE ?",
                (f"%{q}%", f"%{q}%"),
            ).fetchone()[0]
        )
    return int(conn.execute("SELECT COUNT(*) FROM songs").fetchone()[0])


def song_detail(conn: sqlite3.Connection, song_id: int) -> dict | None:
    """Détail d'un morceau : métadonnées + nombre d'empreintes et de hashes distincts."""
    song = get_song(conn, song_id)
    if not song:
        return None
    total, distinct = conn.execute(
        "SELECT COUNT(hash), COUNT(DISTINCT hash) FROM fingerprints WHERE song_id = ?",
        (song_id,),
    ).fetchone()
    song["fingerprints"] = total or 0
    song["distinct_hashes"] = distinct or 0
    return song


def update_song(
    conn: sqlite3.Connection, song_id: int, title: str, artist: str
) -> dict | None:
    """Met à jour titre/artiste d'un morceau (les empreintes ne changent pas)."""
    conn.execute(
        "UPDATE songs SET title = ?, artist = ? WHERE id = ?", (title, artist, song_id)
    )
    conn.commit()
    return get_song(conn, song_id)


def delete_song(conn: sqlite3.Connection, song_id: int) -> bool:
    """Supprime un morceau et ses empreintes (cascade)."""
    cur = conn.execute("DELETE FROM songs WHERE id = ?", (song_id,))
    conn.execute("DELETE FROM fingerprints WHERE song_id = ?", (song_id,))
    conn.commit()
    return cur.rowcount > 0


def stats(conn: sqlite3.Connection) -> dict:
    """Statistiques globales de la base d'empreintes."""
    songs = int(conn.execute("SELECT COUNT(*) FROM songs").fetchone()[0])
    fps = int(conn.execute("SELECT COUNT(*) FROM fingerprints").fetchone()[0])
    distinct = int(conn.execute("SELECT COUNT(DISTINCT hash) FROM fingerprints").fetchone()[0])
    return {
        "songs": songs,
        "fingerprints": fps,
        "distinct_hashes": distinct,
        "avg_fingerprints": round(fps / songs) if songs else 0,
    }
