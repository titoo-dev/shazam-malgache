"""Reconnaissance de bout en bout via la couche de stockage SQLite."""
import numpy as np

from shazam_malgache import db
from shazam_malgache.fingerprint import SAMPLE_RATE, fingerprint
from shazam_malgache.synth import synth_song


def test_sqlite_roundtrip_recognition():
    conn = db.connect(":memory:")
    for seed in (1, 2):
        song_id = db.add_song(conn, title=f"Chanson {seed}", artist="Artiste Test", source="synth")
        db.store_fingerprints(conn, song_id, fingerprint(synth_song(seed)))

    # extrait bruité du morceau seed=1 (t=12s..17s)
    rng = np.random.default_rng(7)
    sr = SAMPLE_RATE
    excerpt = synth_song(1)[12 * sr : 17 * sr].copy() + 0.2 * rng.normal(size=5 * sr)

    results = db.recognize(conn, fingerprint(excerpt))

    assert results, "aucun match"
    assert results[0]["song"]["title"] == "Chanson 1", f"mauvais titre : {results[0]}"
    assert results[0]["score"] >= 8, f"score trop faible : {results[0]}"
