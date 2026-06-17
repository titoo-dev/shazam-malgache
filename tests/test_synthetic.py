"""
Preuve de bout en bout SANS aucune vraie chanson ni réseau.

On fabrique deux "morceaux" synthétiques (mélodies de tons aléatoires distinctes),
on les indexe, puis on prélève un extrait bruité de 5 s du morceau A et on vérifie
que le moteur le reconnaît bien comme A (et pas B), avec un score franc.

C'est la démonstration que le pipeline fingerprint -> index -> match fonctionne.
"""
from collections import defaultdict

import numpy as np

from shazam_malgache.fingerprint import SAMPLE_RATE, fingerprint, match
from shazam_malgache.synth import synth_song


def build_memory_index(songs: dict[int, np.ndarray]):
    """Indexe en mémoire : hash -> [(song_id, offset), ...]."""
    index: dict[int, list[tuple[int, int]]] = defaultdict(list)
    for song_id, samples in songs.items():
        for h, offset in fingerprint(samples):
            index[h].append((song_id, offset))
    return index


def test_recognizes_noisy_excerpt():
    songs = {1: synth_song(seed=1), 2: synth_song(seed=2)}
    index = build_memory_index(songs)
    lookup = lambda h: index.get(h, [])  # noqa: E731

    # Extrait de 5 s du morceau A (t=10s..15s) + bruit gaussien (micro réaliste)
    rng = np.random.default_rng(99)
    sr = SAMPLE_RATE
    excerpt = songs[1][10 * sr : 15 * sr].copy()
    excerpt += 0.2 * rng.normal(size=excerpt.shape)  # bruit ambiant

    results = match(fingerprint(excerpt), lookup)

    assert results, "aucun match trouvé"
    assert results[0]["song_id"] == 1, f"mauvais morceau reconnu : {results[0]}"
    # le bon morceau doit dominer nettement le second
    second = results[1]["score"] if len(results) > 1 else 0
    assert results[0]["score"] >= 8, f"score trop faible : {results}"
    assert results[0]["score"] >= 4 * second, f"match ambigu : {results}"


def test_unknown_excerpt_scores_low():
    """Un morceau jamais indexé ne doit pas matcher fortement."""
    songs = {1: synth_song(seed=1)}
    index = build_memory_index(songs)
    lookup = lambda h: index.get(h, [])  # noqa: E731

    stranger = synth_song(seed=777)[: 5 * SAMPLE_RATE]
    results = match(fingerprint(stranger), lookup)

    top = results[0]["score"] if results else 0
    assert top < 10, f"faux positif : un inconnu matche avec score {top}"
