"""
Moteur d'empreintes audio — algorithme type Shazam.

Principe (Avery Wang, 2003) :
  1. Spectrogramme du signal audio.
  2. Détection des pics spectraux -> "constellation map" (robuste au bruit).
  3. Hachage de PAIRES de pics (ancre + cible + delta-temps) -> empreintes.
  4. Reconnaissance : on aligne les empreintes de l'extrait sur celles de la base
     et on cherche un décalage temporel cohérent (vote majoritaire).

IMPORTANT : une empreinte est IRRÉVERSIBLE. On ne peut pas reconstruire l'audio
à partir des hashes. On ne stocke donc jamais la musique, seulement ces hashes.
C'est exactement le principe de YouTube Content ID et de Shazam.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from typing import Callable, Iterable

import numpy as np
from scipy import signal
from scipy.ndimage import maximum_filter

# --- Paramètres d'analyse (tous ajustables) --------------------------------
SAMPLE_RATE = 11025        # on sous-échantillonne : largement suffisant pour le fingerprint
WINDOW_SIZE = 1024         # taille de la fenêtre FFT
OVERLAP_RATIO = 0.5        # recouvrement entre fenêtres successives
PEAK_NEIGHBORHOOD = 20     # taille du voisinage pour la détection de maxima locaux
AMPLITUDE_FACTOR = 1.0     # seuil = moyenne + facteur * écart-type du spectrogramme
FAN_VALUE = 15             # nombre de pics-cibles appariés à chaque pic-ancre
MIN_DT = 1                 # delta-temps minimal entre ancre et cible (en frames)
MAX_DT = 200               # delta-temps maximal


def compute_spectrogram(samples: np.ndarray, sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Renvoie le spectrogramme en dB, de forme (freq_bins, time_frames)."""
    _f, _t, sxx = signal.spectrogram(
        samples,
        fs=sample_rate,
        nperseg=WINDOW_SIZE,
        noverlap=int(WINDOW_SIZE * OVERLAP_RATIO),
        window="hann",
    )
    return 10.0 * np.log10(sxx + 1e-10)  # +epsilon pour éviter log(0)


def find_peaks(spec: np.ndarray) -> list[tuple[int, int]]:
    """Pics spectraux = maxima locaux au-dessus d'un seuil dynamique.

    Renvoie une liste de (time_frame, freq_bin) triée par temps croissant.
    Le seuil est relatif (moyenne + k*sigma) -> insensible au volume du morceau.
    """
    local_max = maximum_filter(spec, size=PEAK_NEIGHBORHOOD) == spec
    threshold = spec.mean() + AMPLITUDE_FACTOR * spec.std()
    detected = local_max & (spec > threshold)

    freq_idx, time_idx = np.where(detected)
    order = np.argsort(time_idx, kind="stable")
    return list(zip(time_idx[order].tolist(), freq_idx[order].tolist()))


def hash_peaks(peaks: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """Transforme la constellation en empreintes.

    Pour chaque pic-ancre, on l'apparie aux FAN_VALUE pics suivants : le hash
    encode (freq_ancre, freq_cible, delta_temps) sur 30 bits. On renvoie une
    liste de (hash, temps_absolu_de_l_ancre).
    """
    hashes: list[tuple[int, int]] = []
    n = len(peaks)
    for i in range(n):
        t1, f1 = peaks[i]
        for j in range(1, FAN_VALUE + 1):
            if i + j >= n:
                break
            t2, f2 = peaks[i + j]
            dt = t2 - t1
            if MIN_DT <= dt <= MAX_DT:
                h = ((f1 & 0x3FF) << 20) | ((f2 & 0x3FF) << 10) | (dt & 0x3FF)
                hashes.append((h, t1))
    return hashes


def fingerprint(samples: np.ndarray, sample_rate: int = SAMPLE_RATE) -> list[tuple[int, int]]:
    """Pipeline complet : audio -> liste d'empreintes (hash, offset)."""
    samples = np.asarray(samples, dtype=np.float64)
    if samples.ndim > 1:  # stéréo -> mono
        samples = samples.mean(axis=1)
    spec = compute_spectrogram(samples, sample_rate)
    peaks = find_peaks(spec)
    return hash_peaks(peaks)


# --- Reconnaissance --------------------------------------------------------

# Une fonction de lookup prend un hash et renvoie la liste des (song_id, offset)
# stockés en base pour ce hash. On l'abstrait pour pouvoir brancher SQLite,
# Postgres ou un simple dict en mémoire (tests).
LookupFn = Callable[[int], Iterable[tuple[int, int]]]


def match(query_hashes: list[tuple[int, int]], lookup: LookupFn) -> list[dict]:
    """Aligne les empreintes de l'extrait sur la base.

    Pour chaque correspondance de hash, on calcule (offset_base - offset_extrait).
    Le bon morceau est celui dont un MÊME décalage revient le plus souvent :
    cela signifie que tous les pics s'alignent dans le temps. Le 'score' est le
    nombre de pics alignés (proxy de confiance).
    """
    offsets_by_song: dict[int, list[int]] = defaultdict(list)
    for h, query_t in query_hashes:
        for song_id, db_t in lookup(h):
            offsets_by_song[song_id].append(db_t - query_t)

    results: list[dict] = []
    for song_id, diffs in offsets_by_song.items():
        best_offset, score = Counter(diffs).most_common(1)[0]
        results.append(
            {"song_id": song_id, "score": score, "offset_frames": best_offset}
        )
    results.sort(key=lambda r: r["score"], reverse=True)
    return results
