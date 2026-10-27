#!/bin/sh
# Démarrage du conteneur : corpus officiel (PDF) et passages, puis l'API.
set -e
if [ ! -f data/processed/chunks.jsonl ]; then
  # Un document officiel introuvable (déplacé, site indisponible) est signalé dans les journaux,
  # et l'API démarre sans lui plutôt que de rester indisponible.
  python scripts/download_sources.py || echo "AVERTISSEMENT : corpus incomplet, voir ci-dessus"
  python scripts/ingest.py --ignorer-absents
fi
exec uvicorn policy_binder.api:app --host 0.0.0.0 --port "${PORT:-8080}"
