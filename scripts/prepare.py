"""Prépare tout ce qu'il faut pour lancer l'API en local, en une commande.

Usage : uv run python scripts/prepare.py
Enchaîne : téléchargement des 9 PDF officiels, découpage en passages, index dense
(local, ou Qdrant Cloud si QDRANT_URL est défini). S'arrête à la première étape en échec.
"""

import subprocess
import sys
from pathlib import Path

STEPS = ["download_sources.py", "ingest.py", "build_index.py"]


def main() -> int:
    scripts = Path(__file__).resolve().parent
    for step in STEPS:
        print(f"== {step}", flush=True)
        result = subprocess.run([sys.executable, str(scripts / step)], check=False)
        if result.returncode != 0:
            print(f"Échec à l'étape {step} (code {result.returncode}).")
            return result.returncode
    print("Prêt : uv run uvicorn policy_binder.api:app")
    return 0


if __name__ == "__main__":
    sys.exit(main())
