"""
Accès en lecture seule au catalogue d'artistes malgaches (métadonnées Moozik).

Cette base (`catalog.db`, table `catalog_artists`) est constituée à part par
`research/catalog.py` à partir de l'endpoint PUBLIC `/artists` de Moozik. Elle ne
contient QUE des métadonnées factuelles (nom, slug, identifiants industrie,
compteurs) — jamais d'audio. Elle sert de référentiel pour savoir quels artistes
indexer dans le moteur d'empreintes.
"""
from __future__ import annotations

import os
import sqlite3

_FIELDS = [
    "id", "artist_name", "slug", "audio_count", "play_count", "rank",
    "isni_code", "ipi_code", "uuid",
]


def catalog_path() -> str:
    return os.environ.get("CATALOG_DB", "catalog.db")


def _connect() -> sqlite3.Connection | None:
    path = catalog_path()
    if not os.path.exists(path):
        return None
    return sqlite3.connect(path)


def available() -> bool:
    return os.path.exists(catalog_path())


def list_artists(
    q: str = "", sort: str = "rank", limit: int = 50, offset: int = 0
) -> dict:
    """Liste paginée des artistes du catalogue (recherche + tri)."""
    conn = _connect()
    if conn is None:
        return {"total": 0, "artists": [], "available": False}

    order = {
        "rank": "rank ASC",
        "name": "artist_name COLLATE NOCASE ASC",
        "plays": "play_count DESC",
        "tracks": "audio_count DESC",
    }.get(sort, "rank ASC")

    where, params = "", []
    if q:
        where = "WHERE artist_name LIKE ?"
        params = [f"%{q}%"]

    total = int(
        conn.execute(f"SELECT COUNT(*) FROM catalog_artists {where}", params).fetchone()[0]
    )
    rows = conn.execute(
        f"SELECT {','.join(_FIELDS)} FROM catalog_artists {where} "
        f"ORDER BY {order} LIMIT ? OFFSET ?",
        [*params, limit, offset],
    ).fetchall()
    conn.close()
    return {
        "total": total,
        "available": True,
        "artists": [dict(zip(_FIELDS, r)) for r in rows],
    }


def stats() -> dict:
    """Statistiques globales du catalogue de référence."""
    conn = _connect()
    if conn is None:
        return {"available": False, "artists": 0, "tracks": 0}
    artists = int(conn.execute("SELECT COUNT(*) FROM catalog_artists").fetchone()[0])
    tracks = int(
        conn.execute("SELECT COALESCE(SUM(audio_count),0) FROM catalog_artists").fetchone()[0]
    )
    conn.close()
    return {"available": True, "artists": artists, "tracks": tracks}
