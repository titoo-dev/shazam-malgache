"""
Robustesse « over-the-air » (offline, déterministe) : on dégrade un extrait
(bande passante + réverb + bruit) et on vérifie que la bonne chanson gagne quand même.
"""
from collections import defaultdict

import numpy as np

from shazam_malgache.fingerprint import SAMPLE_RATE, fingerprint, match
from shazam_malgache.ota import over_the_air
from shazam_malgache.synth import synth_song


def test_recognition_survives_over_the_air():
    songs = {1: synth_song(seed=1), 2: synth_song(seed=2)}
    index = defaultdict(list)
    for sid, samples in songs.items():
        for h, off in fingerprint(samples):
            index[h].append((sid, off))
    lookup = lambda h: index.get(h, [])  # noqa: E731

    sr = SAMPLE_RATE
    clean = songs[1][10 * sr : 17 * sr]
    degraded = over_the_air(clean, sr)

    results = match(fingerprint(degraded), lookup)

    assert results, "aucun match"
    assert results[0]["song_id"] == 1, f"mauvais morceau : {results[0]}"
    second = results[1]["score"] if len(results) > 1 else 0
    # seuil calibré pour l'audio synthétique (clairsemé) ; la vraie musique score bien plus haut
    assert results[0]["score"] >= 5, f"score trop faible après OTA : {results}"
    assert results[0]["score"] >= 3 * second, f"match ambigu après OTA : {results}"
