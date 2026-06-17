"""
Teste l'API /recognize de bout en bout via le chemin 'upload de fichier' :
on sème un morceau, on poste un extrait wav, on vérifie le titre reconnu.
(Le chemin micro du navigateur utilise exactement le même endpoint.)
"""
import io

import numpy as np
from fastapi.testclient import TestClient
from scipy.io import wavfile

from shazam_malgache import db, ingest
from shazam_malgache.fingerprint import SAMPLE_RATE
from shazam_malgache.synth import synth_song


def _wav_bytes(samples: np.ndarray) -> io.BytesIO:
    buf = io.BytesIO()
    wavfile.write(buf, SAMPLE_RATE, (0.3 * samples).astype(np.float32))
    buf.seek(0)
    return buf


def test_recognize_endpoint(tmp_path, monkeypatch):
    db_path = str(tmp_path / "api.db")
    monkeypatch.setenv("SHAZAM_DB", db_path)

    # on sème un morceau via le pipeline d'ingestion
    conn = db.connect(db_path)
    song = synth_song(1)
    wav = tmp_path / "seed.wav"
    wavfile.write(str(wav), SAMPLE_RATE, (0.3 * song).astype(np.float32))
    ingest.ingest_file(conn, str(wav), title="Veloma", artist="Mpihira Gasy")
    conn.close()

    from shazam_malgache.api import app

    client = TestClient(app)

    # extrait de 5 s -> POST /recognize
    excerpt = song[10 * SAMPLE_RATE : 15 * SAMPLE_RATE]
    resp = client.post("/recognize", files={"file": ("clip.wav", _wav_bytes(excerpt), "audio/wav")})

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["match"] is not None, f"non reconnu : {data}"
    assert data["match"]["title"] == "Veloma", data
    assert data["match"]["score"] >= 8, data


def test_recognize_rejects_empty(tmp_path, monkeypatch):
    monkeypatch.setenv("SHAZAM_DB", str(tmp_path / "empty.db"))
    from shazam_malgache.api import app

    client = TestClient(app)
    resp = client.post("/recognize", files={"file": ("x.wav", io.BytesIO(b""), "audio/wav")})
    assert resp.status_code == 400
