"""API HTTP de l'assistant."""

from functools import lru_cache
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field

from studeria_assistant import __version__
from studeria_assistant.config import get_settings
from studeria_assistant.rag import Answer, Assistant

app = FastAPI(title="Studeria Assistant", version=__version__)


class Question(BaseModel):
    question: str = Field(min_length=3, max_length=500)


@lru_cache(maxsize=1)
def _build_assistant() -> Assistant:
    """Construit l'assistant une seule fois (modèle d'embeddings et index chargés au 1er appel)."""
    from qdrant_client import QdrantClient

    from studeria_assistant.embeddings import FastEmbedEmbedder
    from studeria_assistant.index import DenseIndex
    from studeria_assistant.llm import make_provider

    settings = get_settings()
    key = settings.llm_api_key.get_secret_value() if settings.llm_api_key else None
    index = DenseIndex(QdrantClient(path=str(settings.qdrant_path)), FastEmbedEmbedder())
    llm = make_provider(settings.llm_provider, settings.llm_model, key)
    return Assistant(index, llm, k=settings.top_k)


def get_assistant() -> Assistant:
    if not get_settings().llm_ready:
        raise HTTPException(status_code=503, detail="LLM_API_KEY non configurée.")
    return _build_assistant()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "version": __version__}


@app.post("/ask")
def ask(payload: Question, assistant: Annotated[Assistant, Depends(get_assistant)]) -> Answer:
    return assistant.answer(payload.question)
