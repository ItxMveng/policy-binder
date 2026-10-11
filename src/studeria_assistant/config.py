"""Configuration lue dans l'environnement (ou un fichier .env local non versionné)."""

from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    data_dir: Path = ROOT_DIR / "data"
    mistral_api_key: SecretStr | None = None


def get_settings() -> Settings:
    return Settings()
