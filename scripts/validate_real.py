"""
Track A — validation sur de VRAIES chansons malgaches (YouTube).

Pour chaque URL :
  1. récupère le titre/artiste (yt-dlp, sans télécharger),
  2. télécharge l'audio TRANSITOIREMENT, calcule l'empreinte, stocke (audio jeté),
  3. garde en mémoire un extrait de 10 s (jamais écrit sur disque) pour la validation.

Puis, pour chaque morceau, on bruite son extrait et on vérifie que le moteur le
reconnaît bien (et le distingue des deux autres). Les extraits sont jetés ensuite.

Usage : python -m scripts.validate_real "<url1>" "<url2>" ...
"""
import os
import sys

import numpy as np

from shazam_malgache import audio_io, db
from shazam_malgache.fingerprint import SAMPLE_RATE, fingerprint

def main(urls: list[str]) -> None:
    if not urls:
        print('Usage : python -m scripts.validate_real "<url1>" "<url2>" ...')
        return
    conn = db.connect(os.environ.get("SHAZAM_DB", "shazam.db"))
    held: list[tuple[int, str, np.ndarray]] = []

    print("=== Ingestion (audio jeté, seul le hash reste) ===")
    for url in urls:
        meta = audio_io.fetch_metadata(url)
        samples = audio_io.decode_url(url)               # téléchargement transitoire
        song_id = db.add_song(conn, meta["title"], meta["uploader"], source=url)
        n_hash = db.store_fingerprints(conn, song_id, fingerprint(samples))
        # extrait de 10 s pris au milieu, gardé en mémoire pour la validation
        sr = SAMPLE_RATE
        mid = len(samples) // 2
        excerpt = samples[mid : mid + 10 * sr].copy()
        del samples                                      # audio jeté
        held.append((song_id, meta["title"], excerpt))
        print(f"  • {meta['title']}  —  {meta['uploader']}  ({n_hash} empreintes)")

    print("\n=== Reconnaissance d'extraits bruités (held-out) ===")
    ok = 0
    for song_id, title, excerpt in held:
        rng = np.random.default_rng(song_id)
        noisy = excerpt + 0.5 * float(np.std(excerpt)) * rng.normal(size=excerpt.shape)
        results = db.recognize(conn, fingerprint(noisy))
        top = results[0]
        runner = results[1]["score"] if len(results) > 1 else 0
        good = top["song_id"] == song_id
        ok += int(good)
        conf = round(top["score"] / (top["score"] + runner), 2)
        print(
            f"  {'✅' if good else '❌'} « {title[:38]} »"
            f" -> « {top['song']['title'][:38]} »  (score {top['score']}, conf {conf})"
        )

    print(f"\nRésultat : {ok}/{len(held)} chansons reconnues correctement.")


if __name__ == "__main__":
    main(sys.argv[1:])
