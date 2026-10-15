#!/bin/sh
# Démarrage du conteneur : corpus officiel (PDF) et passages, puis l'API.
set -e
if [ ! -f data/processed/chunks.jsonl ]; then
  python scripts/download_sources.py
  python scripts/ingest.py
fi
exec uvicorn policy_binder.api:app --host 0.0.0.0 --port "${PORT:-8080}"
