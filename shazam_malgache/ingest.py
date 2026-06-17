"""
Ingestion : audio -> empreinte -> stockage.

Règle d'or : l'audio n'est manipulé qu'en mémoire le temps de calculer
l'empreinte, puis il est explicitement jeté (`del samples`). Seul le hash,
irréversible, est conservé. On ne constitue jamais de bibliothèque audio.
"""
from __future__ import annotations

import argparse
import sqlite3

from shazam_malgache import audio_io, db
from shazam_malgache.fingerprint import fingerprint


def _ingest_samples(conn, samples, title, artist, source) -> tuple[int, int]:
    hashes = fingerprint(samples)
    del samples  # <-- l'audio est jeté ici, immédiatement
    song_id = db.add_song(conn, title, artist, source)
    n = db.store_fingerprints(conn, song_id, hashes)
    return song_id, n


def ingest_file(conn, path: str, title: str, artist: str = "", source: str = "file"):
    """Ingest un fichier audio local (mp3, m4a, wav...)."""
    return _ingest_samples(conn, audio_io.decode_file(path), title, artist, source)


def ingest_url(conn, url: str, title: str, artist: str = ""):
    """Ingest depuis une URL (yt-dlp) — audio téléchargé transitoirement puis jeté."""
    return _ingest_samples(conn, audio_io.decode_url(url), title, artist, source=url)


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest un morceau (audio jeté, hash conservé)")
    parser.add_argument("--db", default="shazam.db")
    parser.add_argument("--title", required=True)
    parser.add_argument("--artist", default="")
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--file", help="chemin d'un fichier audio local")
    src.add_argument("--url", help="URL à récupérer via yt-dlp (transitoire)")
    args = parser.parse_args()

    conn = db.connect(args.db)
    if args.file:
        song_id, n = ingest_file(conn, args.file, args.title, args.artist)
    else:
        song_id, n = ingest_url(conn, args.url, args.title, args.artist)
    print(f"OK — '{args.title}' (id={song_id}) : {n} empreintes stockées, audio jeté.")


if __name__ == "__main__":
    main()
