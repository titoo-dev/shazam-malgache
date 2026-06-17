"""
Accès en lecture seule au catalogue d'artistes malgaches (métadonnées Moozik).

Table `catalog_artists` : nom, slug, identifiants industrie, compteurs — jamais
d'audio. Sert de référentiel pour savoir quels artistes indexer.

Backend :
  - PostgreSQL (DATABASE_URL défini) : la table vit dans la base principale ;
  - SQLite : la table vit dans un fichier séparé (CATALOG_DB), constitué par
    `research/catalog.py`.
"""
from __future__ import annotations

import os
import sqlite3

from shazam_malgache import db

_FIELDS = [
    "id", "artist_name", "slug", "audio_count", "play_count", "rank",
    "isni_code", "ipi_code", "uuid",
]


def catalog_path() -> str:
    return os.environ.get("CATALOG_DB", "catalog.db")


def _sqlite_conn() -> sqlite3.Connection | None:
    path = catalog_path()
    if not os.path.exists(path):
        return None
    return sqlite3.connect(path)


def _count() -> int:
    if db.IS_PG:
        conn = db.connect()
        n = int(db.q1(conn, "SELECT COUNT(*) FROM catalog_artists")[0])
        conn.close()
        return n
    conn = _sqlite_conn()
    if conn is None:
        return 0
    n = int(conn.execute("SELECT COUNT(*) FROM catalog_artists").fetchone()[0])
    conn.close()
    return n


def available() -> bool:
    """Vrai si le catalogue contient des artistes."""
    return _count() > 0


def list_artists(search: str = "", sort: str = "rank", limit: int = 50, offset: int = 0) -> dict:
    """Liste paginée des artistes du catalogue (recherche + tri)."""
    like = "ILIKE" if db.IS_PG else "LIKE"
    name_order = "artist_name" if db.IS_PG else "artist_name COLLATE NOCASE"
    order = {
        "rank": "rank ASC",
        "name": f"{name_order} ASC",
        "plays": "play_count DESC",
        "tracks": "audio_count DESC",
    }.get(sort, "rank ASC")

    where, params = "", []
    if search:
        where = f"WHERE artist_name {like} ?"
        params = [f"%{search}%"]
    cols = ",".join(_FIELDS)
    query = (
        f"SELECT {cols} FROM catalog_artists {where} "
        f"ORDER BY {order} LIMIT ? OFFSET ?"
    )

    if db.IS_PG:
        conn = db.connect()
        total = int(db.q1(conn, f"SELECT COUNT(*) FROM catalog_artists {where}", tuple(params))[0])
        rows = db.q(conn, query, (*params, limit, offset))
        conn.close()
    else:
        conn = _sqlite_conn()
        if conn is None:
            return {"total": 0, "artists": [], "available": False}
        total = int(conn.execute(f"SELECT COUNT(*) FROM catalog_artists {where}", params).fetchone()[0])
        rows = conn.execute(query, [*params, limit, offset]).fetchall()
        conn.close()

    return {
        "total": total,
        "available": total > 0 or bool(search),
        "artists": [dict(zip(_FIELDS, r)) for r in rows],
    }


def stats() -> dict:
    """Statistiques globales du catalogue de référence."""
    if db.IS_PG:
        conn = db.connect()
        artists = int(db.q1(conn, "SELECT COUNT(*) FROM catalog_artists")[0])
        tracks = int(db.q1(conn, "SELECT COALESCE(SUM(audio_count),0) FROM catalog_artists")[0])
        conn.close()
        return {"available": artists > 0, "artists": artists, "tracks": tracks}

    conn = _sqlite_conn()
    if conn is None:
        return {"available": False, "artists": 0, "tracks": 0}
    artists = int(conn.execute("SELECT COUNT(*) FROM catalog_artists").fetchone()[0])
    tracks = int(conn.execute("SELECT COALESCE(SUM(audio_count),0) FROM catalog_artists").fetchone()[0])
    conn.close()
    return {"available": artists > 0, "artists": artists, "tracks": tracks}
