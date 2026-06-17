# Contributing to Shazam Malgache

*Misaotra* for helping out! Here's the quick path.

## Setup

```bash
git clone https://github.com/titoo-dev/shazam-malgache && cd shazam-malgache
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"        # you also need `ffmpeg` on your system
pytest -q
```

Prefer Docker? `docker compose run --rm api pytest -q`.

## Ground rules

- **Never commit audio, fingerprint databases, or third-party APKs.** `.gitignore`
  blocks `data/` and `research/` -- keep it that way.
- **Fingerprints only.** Any new ingestion path must drop the audio right after
  hashing (see `del samples` in `ingest.py`). We never persist audio.
- Only fingerprint songs you have the right to (your own, public-domain/CC,
  artist-permissioned, or under a licensing deal).

## Style

- Keep it readable and match the surrounding code. Comments in FR or EN both welcome.
- Add or adjust a test for any behavior change -- tests live in `tests/` and must
  stay **offline and deterministic**.

## Good first issues

- Postgres storage backend behind the existing `db` interface.
- Smarter peak-picking (per-band density caps) for noisier captures.
- A nicer demo UI in `web/index.html`.

*Mankasitraka!*
