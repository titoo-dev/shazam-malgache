"""
Valide le pipeline RÉEL audio : écrit un .wav, le décode via ffmpeg, calcule
l'empreinte, stocke, puis reconnaît un extrait. Aucune dépendance réseau.
(Le chemin yt-dlp partage exactement le même code, à la source de l'audio près.)
"""
import numpy as np
from scipy.io import wavfile

from shazam_malgache import db, ingest
from shazam_malgache.fingerprint import SAMPLE_RATE, fingerprint
from shazam_malgache.synth import synth_song


def test_ingest_wav_file_then_recognize(tmp_path):
    song = synth_song(1)
    wav_path = tmp_path / "morceau.wav"
    wavfile.write(str(wav_path), SAMPLE_RATE, (0.3 * song).astype(np.float32))

    conn = db.connect(":memory:")
    song_id, n = ingest.ingest_file(conn, str(wav_path), title="Tononkira Test", artist="Mpihira")
    assert n > 100, f"trop peu d'empreintes : {n}"

    # extrait bruité de 5 s -> doit être reconnu
    rng = np.random.default_rng(3)
    excerpt = song[10 * SAMPLE_RATE : 15 * SAMPLE_RATE] + 0.2 * rng.normal(size=5 * SAMPLE_RATE)
    results = db.recognize(conn, fingerprint(excerpt))

    assert results[0]["song"]["title"] == "Tononkira Test", f"mauvais titre : {results[0]}"
    assert results[0]["score"] >= 8, f"score trop faible : {results[0]}"
