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
    # Origines autorisées à appeler l'API depuis un navigateur (CORS), séparées par des virgules :
    # ALLOWED_ORIGINS=https://policy-binder.vercel.app,http://localhost:5173
    allowed_origins: str = "http://localhost:5173"
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

    # Protection de la démo publique : questions par adresse IP sur une fenêtre glissante,
    # et quota quotidien global (toutes adresses confondues).
    rate_limit_per_ip: int = 10
    rate_limit_window_s: int = 600
    daily_quota: int = 300
    # Traces Langfuse : activées seulement si les deux clés sont présentes (.env ou secrets).
    langfuse_public_key: str | None = None
    langfuse_secret_key: SecretStr | None = None
    langfuse_host: str = "https://cloud.langfuse.com"

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]

    @property
    def llm_ready(self) -> bool:
        return self.llm_provider == "ollama" or self.llm_api_key is not None

    # Qdrant Cloud en production (URL + clé) ; sans URL, index embarqué dans data/index/qdrant.
    qdrant_url: str | None = None
    qdrant_api_key: SecretStr | None = None

    @property
    def qdrant_path(self) -> Path:
        return self.data_dir / "index" / "qdrant"


def get_settings() -> Settings:
    return Settings()
