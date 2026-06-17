"""
Sème quelques morceaux synthétiques dans la base — smoke-test de l'API et de la page.

(Remarque : un morceau synthétique ne peut pas être reconnu via un micro réel ;
ce seed sert à tester le chemin 'upload de fichier' de l'API. Les vraies chansons
malgaches seront ingérées via shazam_malgache.ingest.)
"""
import os
import tempfile

import numpy as np
from scipy.io import wavfile

from shazam_malgache import db, ingest
from shazam_malgache.fingerprint import SAMPLE_RATE
from shazam_malgache.synth import synth_song

DEMO = [("Veloma", 1), ("Tiako ianao", 2), ("Raha mbola velona", 3)]


def main() -> None:
    conn = db.connect(os.environ.get("SHAZAM_DB", "shazam.db"))
    for title, seed in DEMO:
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        tmp.close()
        wavfile.write(tmp.name, SAMPLE_RATE, (0.3 * synth_song(seed)).astype(np.float32))
        try:
            _id, n = ingest.ingest_file(conn, tmp.name, title, artist="Démo synthétique")
            print(f"  • {title}: {n} empreintes")
        finally:
            os.unlink(tmp.name)
    print("Seed terminé.")


if __name__ == "__main__":
    main()
