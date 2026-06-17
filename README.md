# 🎵 Shazam Malgache 🇲🇬

> *Tongasoa!* Point your mic at a speaker and name that Malagasy tune.
> An open-source, **self-hostable** audio-recognition engine, tuned for the music of Madagascar.

[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![PRs welcome](https://img.shields.io/badge/PRs-welcome-orange)](CONTRIBUTING.md)

Global Shazam doesn't know your *gasy* hits. This gives you the engine to build one that does.
It's a from-scratch, no-black-box implementation of the Shazam-style "constellation"
algorithm, wrapped in a FastAPI backend and a one-button web demo.

**Core principle: it never stores audio.** Only irreversible fingerprints (hashes) —
exactly like Shazam and YouTube Content ID. You can't reconstruct a song from them.

## ✨ Highlights

- 🧠 **Pure-Python engine** — spectrogram → peaks → paired hashes → time-aligned voting. Readable, no magic.
- 🔒 **Fingerprint-only** — irreversible hashes; the audio is dropped right after hashing (`del samples`).
- 🏠 **Self-hostable** — runs entirely on your server. Your catalog never leaves your walls.
- 🎤 **Over-the-air robust** — survives phone-mic-to-speaker (bandpass + reverb + noise), proven by tests.
- 🐳 **One-liner** — `docker compose up` and you're live on `localhost:8000`.
- 🌐 **API + web demo** — a `/recognize` endpoint and a mic-button page.

## 🧠 How it works

```
audio ─▶ spectrogram ─▶ spectral peaks ─▶ hash peak-pairs ─▶ DB
                        (constellation)     (f1, f2, Δt)

mic clip ─▶ same hashes ─▶ look up ─▶ the song whose hashes
                                      line up in time wins 🎯
```

1. **Spectrogram** of the signal.
2. **Spectral peaks** → a noise-robust *constellation map*.
3. **Hash pairs of peaks** `(freq₁, freq₂, Δt)` → compact fingerprints.
4. **Match** by finding the song with a consistent time offset (majority vote).

## 🚀 Quickstart

```bash
git clone https://github.com/titoo-dev/shazam-malgache
cd shazam-malgache
docker compose up -d            # build + serve on http://localhost:8000
```

Open **http://localhost:8000**, hit 🎤, play a song you've added — get the title.

Smoke-test the API with a few synthetic tracks:

```bash
docker compose exec api python -m scripts.seed_synthetic
```

## 🎚️ Add real songs

Fingerprint a track you have the rights to (audio is dropped, only the hash is kept):

```bash
# from a local file
docker compose exec api shazam-mlg-ingest --db /data/shazam.db \
  --title "Namany" --artist "Vazo Lee" --file /data/namany.mp3

# from a URL (yt-dlp, transient download)
docker compose exec api shazam-mlg-ingest --db /data/shazam.db \
  --title "Namany" --artist "Vazo Lee" --url "https://youtu.be/…"
```

## 🧪 Tests

```bash
docker compose run --rm api pytest -q
```

## 🗂️ Layout

```
shazam_malgache/      # the engine (importable package)
  fingerprint.py      #   constellation algorithm + matching
  db.py               #   SQLite storage (metadata + hashes, never audio)
  audio_io.py         #   ffmpeg / yt-dlp decoding (transient)
  ingest.py           #   audio → fingerprint → store
  api.py              #   FastAPI: /recognize, /songs
  ota.py              #   over-the-air degradation (robustness tests)
  synth.py            #   synthetic songs for offline tests
web/index.html        # one-button mic demo
scripts/              # seed, validate, diagnose
tests/                # pytest suite (offline, deterministic)
```

## 🤝 The ethics bit (please read)

This is a tool to **recognize** music, not to pirate it.

- We store **fingerprints, never audio.**
- Only fingerprint songs you have the right to (your own, public-domain/CC,
  artist-permissioned, or under a licensing deal).
- Don't scrape someone else's catalog. To power recognition over a licensed
  library, **partner with the rights-holder** and run this engine on their
  infrastructure — the audio never has to move.

## 🛣️ Roadmap

- [ ] Postgres backend + sharded hash index for catalog scale
- [ ] Lyrics sync on match (shout-out to the Malagasy `tononkira` scene 👀)
- [ ] Mobile SDK for the "Shazam button"
- [ ] Larger, properly-sourced demo corpus

## 🙌 Contributing

PRs welcome — see [CONTRIBUTING.md](CONTRIBUTING.md).

## 📄 License

[MIT](LICENSE) — do good things with it.

---

<p align="center"><i>Made with ❤️ in Madagascar. Veloma!</i></p>
