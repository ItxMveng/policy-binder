"""Liste des documents sources (data/sources.yaml) et leur téléchargement."""

import hashlib
from datetime import date
from pathlib import Path

import httpx
import yaml
from pydantic import BaseModel, HttpUrl

USER_AGENT = "policy-binder/0.1 (+https://github.com/ItxMveng/policy-binder)"


class Source(BaseModel):
    id: str
    title: str
    institution: str
    kind: str
    url: HttpUrl
    consulted_on: date


class SourceList(BaseModel):
    sources: list[Source]


def load_sources(path: Path) -> list[Source]:
    """Charge et valide la liste des sources ; les identifiants doivent être uniques."""
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    sources = SourceList.model_validate(raw).sources
    ids = [source.id for source in sources]
    duplicates = {i for i in ids if ids.count(i) > 1}
    if duplicates:
        raise ValueError(f"identifiants en double : {sorted(duplicates)}")
    return sources


def raw_pdf_path(raw_dir: Path, source: Source) -> Path:
    return raw_dir / f"{source.id}.pdf"


def download_source(client: httpx.Client, source: Source, raw_dir: Path) -> str:
    """Télécharge un PDF dans raw_dir et renvoie son empreinte SHA-256.

    Lève une erreur si la réponse n'est pas un PDF : on ne veut pas indexer une page d'erreur HTML.
    """
    response = client.get(str(source.url), follow_redirects=True)
    response.raise_for_status()
    content = response.content
    if not content.startswith(b"%PDF"):
        raise ValueError(f"{source.id} : la réponse n'est pas un PDF")
    raw_dir.mkdir(parents=True, exist_ok=True)
    raw_pdf_path(raw_dir, source).write_bytes(content)
    return hashlib.sha256(content).hexdigest()


def make_client() -> httpx.Client:
    return httpx.Client(timeout=60.0, headers={"User-Agent": USER_AGENT})
