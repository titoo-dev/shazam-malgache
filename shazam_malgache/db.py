"""
Stockage persistant des empreintes — SQLite par défaut, PostgreSQL en option.

On ne stocke QUE des métadonnées (titre/artiste) et des empreintes (hashes
irréversibles). Jamais d'audio.

Backend :
  - par défaut : SQLite (fichier), idéal en local et pour les tests (offline) ;
  - si la variable d'environnement DATABASE_URL est définie (postgres://…), tout
    passe sur PostgreSQL. Les signatures publiques sont identiques dans les deux
    cas : le reste du code (api, ingest, jobs, catalog) ne change pas.

La colonne `offset` est un mot réservé en PostgreSQL : on la cite toujours
("offset"), ce qui reste valide en SQLite.
"""
from __future__ import annotations

import os
import sqlite3
from typing import Iterable

from shazam_malgache.fingerprint import LookupFn, match

DATABASE_URL = os.environ.get("DATABASE_URL", "")
IS_PG = DATABASE_URL.startswith("postgres")

# --- Schémas (par dialecte) -------------------------------------------------
_SCHEMA_SQLITE = """
CREATE TABLE IF NOT EXISTS songs (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    title   TEXT NOT NULL,
    artist  TEXT,
    source  TEXT,
    UNIQUE(title, artist)
);
CREATE TABLE IF NOT EXISTS fingerprints (
    hash    INTEGER NOT NULL,
    song_id INTEGER NOT NULL REFERENCES songs(id) ON DELETE CASCADE,
    "offset" INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_fp_hash ON fingerprints(hash);
"""

_SCHEMA_PG = """
CREATE TABLE IF NOT EXISTS songs (
    id      SERIAL PRIMARY KEY,
    title   TEXT NOT NULL,
    artist  TEXT NOT NULL DEFAULT '',
    source  TEXT,
    UNIQUE(title, artist)
);
CREATE TABLE IF NOT EXISTS fingerprints (
    hash    BIGINT NOT NULL,
    song_id INTEGER NOT NULL REFERENCES songs(id) ON DELETE CASCADE,
    "offset" INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_fp_hash ON fingerprints(hash);
CREATE TABLE IF NOT EXISTS catalog_artists (
    id INTEGER PRIMARY KEY, artist_name TEXT, slug TEXT, audio_count INTEGER,
    play_count INTEGER, rank INTEGER, isni_code TEXT, ipi_code TEXT, uuid TEXT
);
"""


# --- Connexion + helpers de dialecte ----------------------------------------

def connect(path: str = "shazam.db"):
    """Ouvre une connexion (SQLite ou PostgreSQL) et garantit le schéma."""
    if IS_PG:
        import psycopg2

        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = True  # chaque instruction est validée immédiatement
        with conn.cursor() as cur:
            cur.execute(_SCHEMA_PG)
        return conn

    conn = sqlite3.connect(path, timeout=30.0)
    conn.execute("PRAGMA foreign_keys = ON")
    # Plusieurs workers d'ingestion peuvent écrire en parallèle : on patiente
    # plutôt que d'échouer immédiatement sur un verrou.
    conn.execute("PRAGMA busy_timeout = 30000")
    conn.executescript(_SCHEMA_SQLITE)
    return conn


def sql(s: str) -> str:
    """Adapte les paramètres positionnels au dialecte (? -> %s en PostgreSQL)."""
    return s.replace("?", "%s") if IS_PG else s


def q(conn, query: str, params: tuple = ()) -> list:
    """Exécute une requête et renvoie toutes les lignes."""
    if IS_PG:
        with conn.cursor() as cur:
            cur.execute(sql(query), params)
            return cur.fetchall()
    return conn.execute(query, params).fetchall()


def q1(conn, query: str, params: tuple = ()):
    rows = q(conn, query, params)
    return rows[0] if rows else None


def execute(conn, query: str, params: tuple = ()) -> int:
    """Exécute une écriture (INSERT/UPDATE/DELETE) et renvoie le nombre de lignes."""
    if IS_PG:
        with conn.cursor() as cur:
            cur.execute(sql(query), params)
            return cur.rowcount
    cur = conn.execute(query, params)
    conn.commit()
    return cur.rowcount


# --- Morceaux ---------------------------------------------------------------

def add_song(conn, title: str, artist: str = "", source: str = "") -> int:
    """Insère un morceau (ou récupère l'id existant si déjà présent)."""
    if IS_PG:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO songs(title, artist, source) VALUES (%s, %s, %s) "
                "ON CONFLICT (title, artist) DO NOTHING RETURNING id",
                (title, artist, source),
            )
            row = cur.fetchone()
            if row:
                return int(row[0])
            cur.execute(
                "SELECT id FROM songs WHERE title = %s AND artist = %s", (title, artist)
            )
            return int(cur.fetchone()[0])

    cur = conn.execute(
        "INSERT OR IGNORE INTO songs(title, artist, source) VALUES (?, ?, ?)",
        (title, artist, source),
    )
    if cur.lastrowid and cur.rowcount:
        conn.commit()
        return cur.lastrowid
    row = conn.execute(
        "SELECT id FROM songs WHERE title = ? AND artist = ?", (title, artist)
    ).fetchone()
    return int(row[0])


def store_fingerprints(conn, song_id: int, hashes: Iterable[tuple[int, int]]) -> int:
    """Stocke les empreintes (hash, offset) d'un morceau."""
    rows = [(int(h), song_id, int(offset)) for h, offset in hashes]
    if not rows:
        return 0
    if IS_PG:
        from psycopg2.extras import execute_values

        with conn.cursor() as cur:
            execute_values(
                cur,
                'INSERT INTO fingerprints(hash, song_id, "offset") VALUES %s',
                rows,
            )
        return len(rows)

    conn.executemany(
        'INSERT INTO fingerprints(hash, song_id, "offset") VALUES (?, ?, ?)', rows
    )
    conn.commit()
    return len(rows)


def get_song(conn, song_id: int) -> dict | None:
    row = q1(conn, "SELECT id, title, artist, source FROM songs WHERE id = ?", (song_id,))
    if not row:
        return None
    return {"id": row[0], "title": row[1], "artist": row[2], "source": row[3]}


# --- Reconnaissance ---------------------------------------------------------

def _fingerprint_index(conn, hashes: list[int]) -> dict[int, list[tuple[int, int]]]:
    """Récupère en un minimum de requêtes les (song_id, offset) des hashes donnés."""
    from collections import defaultdict

    index: dict[int, list[tuple[int, int]]] = defaultdict(list)
    uniq = list({int(h) for h in hashes})
    if not uniq:
        return index

    if IS_PG:
        with conn.cursor() as cur:
            cur.execute(
                'SELECT hash, song_id, "offset" FROM fingerprints WHERE hash = ANY(%s)',
                (uniq,),
            )
            for h, song_id, offset in cur.fetchall():
                index[h].append((song_id, offset))
        return index

    # SQLite : on chunke le IN (...) pour rester sous la limite de paramètres.
    for i in range(0, len(uniq), 800):
        chunk = uniq[i : i + 800]
        placeholders = ",".join("?" * len(chunk))
        rows = conn.execute(
            f'SELECT hash, song_id, "offset" FROM fingerprints WHERE hash IN ({placeholders})',
            chunk,
        ).fetchall()
        for h, song_id, offset in rows:
            index[h].append((song_id, offset))
    return index


def make_lookup(conn) -> LookupFn:
    """Renvoie une fonction hash -> [(song_id, offset), ...] (requête par hash)."""

    def lookup(h: int):
        return q(
            conn, 'SELECT song_id, "offset" FROM fingerprints WHERE hash = ?', (h,)
        )

    return lookup


def recognize(conn, query_hashes: list[tuple[int, int]], top_k: int = 5):
    """Reconnaît un extrait et renvoie les meilleurs candidats enrichis des métadonnées.

    On charge en une fois toutes les empreintes pertinentes (lookup batché), ce
    qui évite des milliers d'aller-retours SQL — crucial sur PostgreSQL.
    """
    index = _fingerprint_index(conn, [h for h, _ in query_hashes])
    results = match(query_hashes, lambda h: index.get(h, []))[:top_k]
    for r in results:
        r["song"] = get_song(conn, r["song_id"])
    return results


# --- Administration / gestion ----------------------------------------------

def list_songs(conn, search: str = "", limit: int = 50, offset: int = 0) -> list[dict]:
    """Liste les morceaux indexés avec leur nombre d'empreintes (recherche optionnelle)."""
    where, params = "", []
    if search:
        where = "WHERE s.title LIKE ? OR s.artist LIKE ?"
        params = [f"%{search}%", f"%{search}%"]
    rows = q(
        conn,
        f"""
        SELECT s.id, s.title, s.artist, s.source, COUNT(f.hash) AS fp
        FROM songs s
        LEFT JOIN fingerprints f ON f.song_id = s.id
        {where}
        GROUP BY s.id, s.title, s.artist, s.source
        ORDER BY s.id DESC
        LIMIT ? OFFSET ?
        """,
        (*params, limit, offset),
    )
    return [
        {"id": r[0], "title": r[1], "artist": r[2], "source": r[3], "fingerprints": int(r[4])}
        for r in rows
    ]


def count_songs(conn, search: str = "") -> int:
    if search:
        row = q1(
            conn,
            "SELECT COUNT(*) FROM songs WHERE title LIKE ? OR artist LIKE ?",
            (f"%{search}%", f"%{search}%"),
        )
    else:
        row = q1(conn, "SELECT COUNT(*) FROM songs")
    return int(row[0])


def song_detail(conn, song_id: int) -> dict | None:
    """Détail d'un morceau : métadonnées + nombre d'empreintes et de hashes distincts."""
    song = get_song(conn, song_id)
    if not song:
        return None
    row = q1(
        conn,
        "SELECT COUNT(hash), COUNT(DISTINCT hash) FROM fingerprints WHERE song_id = ?",
        (song_id,),
    )
    song["fingerprints"] = int(row[0] or 0)
    song["distinct_hashes"] = int(row[1] or 0)
    return song


def update_song(conn, song_id: int, title: str, artist: str) -> dict | None:
    """Met à jour titre/artiste d'un morceau (les empreintes ne changent pas)."""
    execute(conn, "UPDATE songs SET title = ?, artist = ? WHERE id = ?", (title, artist, song_id))
    return get_song(conn, song_id)


def delete_song(conn, song_id: int) -> bool:
    """Supprime un morceau et ses empreintes (cascade)."""
    execute(conn, "DELETE FROM fingerprints WHERE song_id = ?", (song_id,))
    n = execute(conn, "DELETE FROM songs WHERE id = ?", (song_id,))
    return n > 0


def stats(conn) -> dict:
    """Statistiques globales de la base d'empreintes."""
    songs = int(q1(conn, "SELECT COUNT(*) FROM songs")[0])
    fps = int(q1(conn, "SELECT COUNT(*) FROM fingerprints")[0])
    distinct = int(q1(conn, "SELECT COUNT(DISTINCT hash) FROM fingerprints")[0])
    return {
        "songs": songs,
        "fingerprints": fps,
        "distinct_hashes": distinct,
        "avg_fingerprints": round(fps / songs) if songs else 0,
    }
