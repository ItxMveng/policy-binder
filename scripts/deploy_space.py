"""Publie l'API sur un Space Hugging Face (SDK Docker) et y règle les secrets d'exécution.

Usage (GitHub Actions) : uv run python scripts/deploy_space.py
Variables d'environnement : HF_TOKEN, HF_SPACE (« utilisateur/nom »), et les secrets d'exécution
(LLM_API_KEY, QDRANT_URL, QDRANT_API_KEY, LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY) ainsi que
ALLOWED_ORIGINS (JSON). Les secrets passent directement des secrets GitHub au Space.
"""

import os
import shutil
import sys
import tempfile
from pathlib import Path

from huggingface_hub import HfApi

ROOT = Path(__file__).resolve().parents[1]
SECRETS = [
    "LLM_API_KEY",
    "QDRANT_URL",
    "QDRANT_API_KEY",
    "LANGFUSE_PUBLIC_KEY",
    "LANGFUSE_SECRET_KEY",
]
VARIABLES = ["ALLOWED_ORIGINS", "LLM_PROVIDER", "LLM_MODEL"]


def stage(target: Path) -> None:
    """Copie seulement ce que le build du Space utilise (aucune donnée, aucun secret)."""
    shutil.copy(ROOT / "deploy" / "space" / "Dockerfile", target / "Dockerfile")
    shutil.copy(ROOT / "deploy" / "space" / "README.md", target / "README.md")
    for name in ("pyproject.toml", "uv.lock"):
        shutil.copy(ROOT / name, target / name)
    shutil.copytree(ROOT / "src", target / "src", ignore=shutil.ignore_patterns("__pycache__"))
    (target / "scripts").mkdir()
    for script in ("download_sources.py", "ingest.py"):
        shutil.copy(ROOT / "scripts" / script, target / "scripts" / script)
    (target / "data").mkdir()
    shutil.copy(ROOT / "data" / "sources.yaml", target / "data" / "sources.yaml")


def main() -> int:
    space = os.environ["HF_SPACE"]
    api = HfApi(token=os.environ["HF_TOKEN"])
    api.create_repo(space, repo_type="space", space_sdk="docker", exist_ok=True)
    for name in SECRETS:
        value = os.environ.get(name)
        if value:
            api.add_space_secret(space, name, value)
    for name in VARIABLES:
        value = os.environ.get(name)
        if value:
            api.add_space_variable(space, name, value)
    with tempfile.TemporaryDirectory() as folder:
        stage(Path(folder))
        api.upload_folder(
            repo_id=space,
            repo_type="space",
            folder_path=folder,
            commit_message=f"Déploiement depuis GitHub {os.environ.get('GITHUB_SHA', 'local')[:7]}",
            delete_patterns=["*"],
        )
    print(f"Space publié : https://huggingface.co/spaces/{space}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
