"""
Simulation « over-the-air » : dégrade un signal propre pour imiter une capture
micro d'une enceinte (bande passante téléphone + réverb de pièce + bruit + AGC).
Utilisé pour tester/durcir la robustesse de la reconnaissance.
"""
from __future__ import annotations

import numpy as np
from scipy import signal


def room_ir(sr: int, t60: float = 0.18) -> np.ndarray:
    """Réponse impulsionnelle de pièce synthétique (bruit en décroissance expo)."""
    n = int(t60 * sr)
    rng = np.random.default_rng(0)
    ir = rng.normal(size=n) * np.exp(-np.arange(n) / (t60 * sr / 3))
    ir[0] += 1.0  # trajet direct
    return ir / np.sqrt(np.sum(ir**2))


def over_the_air(x: np.ndarray, sr: int, snr_db: float = 12.0) -> np.ndarray:
    """Dégrade un signal propre pour imiter une capture micro d'une enceinte."""
    sos = signal.butter(4, [200, 5000], btype="band", fs=sr, output="sos")
    y = signal.sosfilt(sos, x)                                   # bande passante tél.
    y = signal.fftconvolve(y, room_ir(sr))[: len(x)]            # réverb pièce
    rng = np.random.default_rng(1)
    power = float(np.mean(y**2)) + 1e-9
    noise_power = power / (10 ** (snr_db / 10))
    y = y + rng.normal(scale=np.sqrt(noise_power), size=len(y))  # bruit ambiant
    y = y / (np.max(np.abs(y)) + 1e-9)
    return np.clip(y * 1.2, -1, 1).astype(np.float32)            # AGC + léger clipping
