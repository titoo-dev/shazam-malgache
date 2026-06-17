"""
Génération d'audio synthétique (mélodies de tons aléatoires).

Utilisé par les tests et le seed de démo pour disposer de "morceaux" reproductibles
sans aucun fichier ni réseau. Chaque `seed` produit une signature spectrale unique.
"""
from __future__ import annotations

import numpy as np

from shazam_malgache.fingerprint import SAMPLE_RATE


def synth_song(seed: int, duration_s: float = 30.0, sr: int = SAMPLE_RATE) -> np.ndarray:
    """Mélodie de tons courts tirés au hasard -> signature unique par `seed`."""
    rng = np.random.default_rng(seed)
    t = np.arange(int(duration_s * sr)) / sr
    out = np.zeros_like(t)
    note_len = 0.25  # secondes par note
    n_notes = int(duration_s / note_len)
    for k in range(n_notes):
        freq = rng.uniform(200, 2500)
        start, end = int(k * note_len * sr), int((k + 1) * note_len * sr)
        local_t = t[start:end]
        out[start:end] += np.sin(2 * np.pi * freq * local_t)
        out[start:end] += 0.5 * np.sin(2 * np.pi * 2 * freq * local_t)  # harmonique
    return out
