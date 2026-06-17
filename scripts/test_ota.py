"""
Test de robustesse « over-the-air » : simule une capture micro→enceinte
(bande passante téléphone + réverb de pièce + bruit ambiant + AGC/clipping)
et vérifie que la reconnaissance tient toujours.

Usage : python -m scripts.test_ota [url_youtube] [chemin_db]
"""
import sys

import numpy as np

from shazam_malgache import audio_io, db
from shazam_malgache.fingerprint import SAMPLE_RATE, fingerprint
from shazam_malgache.ota import over_the_air


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage : python -m scripts.test_ota <url_youtube> [chemin_db]")
        return
    url = sys.argv[1]
    db_path = sys.argv[2] if len(sys.argv) > 2 else "/data/shazam.db"
    conn = db.connect(db_path)

    samples = audio_io.decode_url(url)        # téléchargement transitoire (1 morceau)
    sr = SAMPLE_RATE
    mid = len(samples) // 2
    clean = samples[mid : mid + 7 * sr].astype(np.float32)
    del samples

    for label, clip in [("propre", clean),
                        ("over-the-air simulé", over_the_air(clean, sr)),
                        ("OTA + SNR 6 dB", over_the_air(clean, sr, snr_db=6.0))]:
        res = db.recognize(conn, fingerprint(clip))
        if res:
            top = res[0]
            runner = res[1]["score"] if len(res) > 1 else 0
            print(f"  {label:22} -> {top['song']['title'][:42]}  (score {top['score']}, 2e {runner})")
        else:
            print(f"  {label:22} -> AUCUN MATCH")


if __name__ == "__main__":
    main()
