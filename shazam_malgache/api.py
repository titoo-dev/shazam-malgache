"""
API de reconnaissance + page de démo.

POST /recognize : reçoit un extrait audio (micro ou fichier), calcule l'empreinte,
                  interroge la base et renvoie le titre reconnu. L'audio reçu est
                  jeté après le calcul du hash (fichier temporaire supprimé).
GET  /           : page web de démo (capture micro / upload).
GET  /songs      : liste des morceaux indexés.
"""
from __future__ import annotations

import os
import tempfile

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import HTMLResponse

from shazam_malgache import audio_io, db
from shazam_malgache.fingerprint import fingerprint

# Score minimal pour considérer qu'on a une vraie correspondance (réglable).
MIN_SCORE = 5

app = FastAPI(title="Shazam Malgache", version="0.1.0")


def _db_path() -> str:
    return os.environ.get("SHAZAM_DB", "shazam.db")


@app.get("/", response_class=HTMLResponse)
def home() -> str:
    page = os.path.join(os.path.dirname(__file__), "..", "web", "index.html")
    with open(page, encoding="utf-8") as f:
        return f.read()


@app.get("/songs")
def songs() -> dict:
    conn = db.connect(_db_path())
    rows = conn.execute("SELECT id, title, artist FROM songs ORDER BY title").fetchall()
    conn.close()
    return {"count": len(rows), "songs": [{"id": r[0], "title": r[1], "artist": r[2]} for r in rows]}


@app.post("/recognize")
async def recognize(file: UploadFile = File(...)) -> dict:
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="fichier audio vide")

    # On écrit l'upload dans un fichier temporaire le temps du décodage, puis on le supprime.
    suffix = os.path.splitext(file.filename or "")[1] or ".bin"
    tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    try:
        tmp.write(data)
        tmp.close()
        samples = audio_io.decode_file(tmp.name)
    except Exception as exc:  # décodage impossible
        raise HTTPException(status_code=400, detail=f"audio illisible: {exc}") from exc
    finally:
        os.unlink(tmp.name)  # <-- audio jeté

    hashes = fingerprint(samples)
    del samples  # <-- échantillons jetés, seul le hash subsiste

    conn = db.connect(_db_path())
    results = db.recognize(conn, hashes, top_k=3)
    conn.close()

    if not results or results[0]["score"] < MIN_SCORE:
        return {"match": None, "candidates": results}

    top = results[0]
    runner = results[1]["score"] if len(results) > 1 else 0
    return {
        "match": {
            "title": top["song"]["title"],
            "artist": top["song"]["artist"],
            "score": top["score"],
            # confiance grossière : domination sur le 2e candidat
            "confidence": round(top["score"] / (top["score"] + runner), 2),
        },
        "candidates": results,
    }
