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
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA foreign_keys = ON")
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
