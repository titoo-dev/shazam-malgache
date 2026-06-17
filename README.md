# Shazam Malgache

Recognize Malagasy songs from a short audio clip. A self-hostable, Shazam-style
audio-recognition engine. It stores only fingerprints, never audio.

## Requirements

Either:

- **Docker** + Docker Compose (recommended), or
- **Python 3.10+** and **ffmpeg** installed on your system.

## Install & run with Docker

```bash
git clone https://github.com/titoo-dev/shazam-malgache
cd shazam-malgache
docker compose up -d
```

Open http://localhost:8000

## Install & run without Docker

```bash
git clone https://github.com/titoo-dev/shazam-malgache
cd shazam-malgache
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e .
uvicorn shazam_malgache.api:app
```

Open http://localhost:8000

## Add a song

The audio is read only to compute its fingerprint, then dropped.

With Docker:

```bash
# from a local file
docker compose exec api shazam-mlg-ingest --db /data/shazam.db \
  --title "Namany" --artist "Vazo Lee" --file /data/namany.mp3

# from a URL
docker compose exec api shazam-mlg-ingest --db /data/shazam.db \
  --title "Namany" --artist "Vazo Lee" --url "https://youtu.be/..."
```

Without Docker (same commands, drop `docker compose exec api`):

```bash
shazam-mlg-ingest --title "Namany" --artist "Vazo Lee" --file namany.mp3
```

## Try it

Open http://localhost:8000, click the mic button, play a song you added, and
the title appears.

No songs yet? Seed a few synthetic ones to test the setup:

```bash
docker compose exec api python -m scripts.seed_synthetic
```

## Run the tests

```bash
docker compose run --rm api pytest -q
```

## License

[MIT](LICENSE)
