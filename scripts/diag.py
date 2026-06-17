"""Diagnostic : courbe score vs niveau de bruit, pour calibrer les paramètres."""
import numpy as np

from shazam_malgache.fingerprint import SAMPLE_RATE, fingerprint, match
from shazam_malgache.synth import synth_song
from tests.test_synthetic import build_memory_index

songs = {1: synth_song(1), 2: synth_song(2)}
index = build_memory_index(songs)
lookup = lambda h: index.get(h, [])  # noqa: E731

print("empreintes par morceau :", {sid: len(fingerprint(s)) for sid, s in songs.items()})

sr = SAMPLE_RATE
for noise in [0.0, 0.05, 0.1, 0.2, 0.4]:
    rng = np.random.default_rng(99)
    exc = songs[1][10 * sr : 15 * sr].copy()
    exc = exc + noise * rng.normal(size=exc.shape)
    qh = fingerprint(exc)
    res = match(qh, lookup)
    print(f"bruit={noise:<4} q_hashes={len(qh):<5} top3={[(r['song_id'], r['score']) for r in res[:3]]}")
