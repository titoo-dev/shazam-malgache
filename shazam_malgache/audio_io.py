"""
Décodage audio -> échantillons mono.

Toute entrée (mp3, m4a, wav, flux yt-dlp) est convertie en float32 mono à
SAMPLE_RATE via ffmpeg. L'audio n'existe qu'en mémoire / en fichier temporaire
le temps du calcul de l'empreinte, puis il est jeté. Rien n'est conservé.
"""
from __future__ import annotations

import os
import subprocess
import tempfile

import numpy as np

from shazam_malgache.fingerprint import SAMPLE_RATE


def fetch_metadata(url: str) -> dict:
    """Récupère titre/artiste/durée via yt-dlp SANS télécharger l'audio."""
    proc = subprocess.run(
        [
            "yt-dlp", "-q", "--no-playlist", "--skip-download",
            "--print", "%(title)s\t%(uploader)s\t%(duration)s",
            url,
        ],
        capture_output=True, text=True, check=True,
    )
    title, uploader, duration = (proc.stdout.strip().split("\t") + ["", "", ""])[:3]
    return {"title": title or url, "uploader": uploader, "duration": duration}


def decode_file(path: str, sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Décode un fichier audio en float32 mono via ffmpeg."""
    cmd = [
        "ffmpeg", "-v", "error",
        "-i", path,
        "-ac", "1",                 # mono
        "-ar", str(sample_rate),    # ré-échantillonnage
        "-f", "f32le",              # PCM float 32 bits little-endian
        "-",                        # vers stdout
    ]
    proc = subprocess.run(cmd, capture_output=True, check=True)
    return np.frombuffer(proc.stdout, dtype=np.float32)


def decode_url(url: str, sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Récupère l'audio d'une URL (yt-dlp) de façon TRANSITOIRE puis le décode.

    Le fichier temporaire est supprimé immédiatement après le décodage : on ne
    conserve jamais l'audio, seulement les échantillons en mémoire le temps de
    calculer l'empreinte (l'appelant jette ensuite ces échantillons).
    """
    tmpdir = tempfile.mkdtemp(prefix="shz_")
    out_tpl = os.path.join(tmpdir, "audio.%(ext)s")
    try:
        subprocess.run(
            # --no-playlist : ne récupérer QUE la vidéo, jamais le mix/playlist (?list=...)
            ["yt-dlp", "-q", "--no-playlist", "-f", "bestaudio", "-o", out_tpl, url],
            check=True,
        )
        files = [os.path.join(tmpdir, f) for f in os.listdir(tmpdir)]
        if not files:
            raise RuntimeError(f"yt-dlp n'a rien téléchargé pour {url}")
        return decode_file(files[0], sample_rate)
    finally:
        # on jette l'audio quoi qu'il arrive
        for f in os.listdir(tmpdir):
            try:
                os.remove(os.path.join(tmpdir, f))
            except OSError:
                pass
        os.rmdir(tmpdir)
