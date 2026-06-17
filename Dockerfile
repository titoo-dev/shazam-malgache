FROM python:3.12-slim

# ffmpeg : décodage audio (mp3/m4a/webm/...) pour l'ingestion
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . .
RUN pip install --no-cache-dir -e ".[dev]"

ENV PYTHONPATH=/app
CMD ["pytest", "-q"]
