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

    from studeria_assistant.bm25 import BM25Index
    from studeria_assistant.embeddings import FastEmbedEmbedder
    from studeria_assistant.hybrid import HybridRetriever
    from studeria_assistant.index import DenseIndex
    from studeria_assistant.ingest import read_chunks
    from studeria_assistant.llm import make_provider
    from studeria_assistant.rag import Retriever

    settings = get_settings()
    key = settings.llm_api_key.get_secret_value() if settings.llm_api_key else None
    retriever: Retriever = DenseIndex(
        QdrantClient(path=str(settings.qdrant_path)), FastEmbedEmbedder()
    )
    if settings.retrieval == "hybride":
        chunks = read_chunks(settings.data_dir / "processed" / "chunks.jsonl")
        retriever = HybridRetriever(retriever, BM25Index(chunks))
    min_score = None
    if settings.rerank:
        from studeria_assistant.rerank import FastEmbedReranker, RerankingRetriever

        retriever = RerankingRetriever(
            retriever, FastEmbedReranker(), settings.rerank_candidates, settings.rerank_max_chars
        )
        min_score = settings.min_score
    llm = make_provider(settings.llm_provider, settings.llm_model, key)
    return Assistant(retriever, llm, k=settings.top_k, min_score=min_score)


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
