"""Configuration lue dans l'environnement (ou un fichier .env local non versionné)."""

from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    data_dir: Path = ROOT_DIR / "data"
    # Fournisseur LLM : "groq" (offre gratuite), "mistral" (payant) ou "ollama" (local, sans clé).
    llm_provider: str = "groq"
    llm_model: str = "openai/gpt-oss-120b"
    llm_api_key: SecretStr | None = None
    top_k: int = 5
    # "hybride" (dense + BM25, retenu après mesure, voir docs/evaluation.md) ou "dense".
    retrieval: str = "hybride"
    # Reranking : réglage complet (20 candidats, passages entiers), le seul dont le gain est mesuré
    # (docs/evaluation.md). Coût : environ 10 s par requête sur un CPU de portable.
    rerank: bool = True
    rerank_candidates: int = 20
    rerank_max_chars: int | None = None
    # Seuil d'abstention sur le score du reranker, appliqué seulement si rerank=True.
    # Valeurs calibrées (eval/results/calibration*.json) : -2.362 (20 candidats, passages entiers),
    # -6.582 (10 candidats, 400 caractères). None = pas de seuil.
    min_score: float | None = -2.362

    @property
    def llm_ready(self) -> bool:
        return self.llm_provider == "ollama" or self.llm_api_key is not None

    @property
    def qdrant_path(self) -> Path:
        return self.data_dir / "index" / "qdrant"


def get_settings() -> Settings:
    return Settings()
