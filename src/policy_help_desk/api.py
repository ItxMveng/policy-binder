"""API HTTP de l'assistant."""

from functools import lru_cache
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field

from policy_help_desk import __version__
from policy_help_desk.config import get_settings
from policy_help_desk.rag import Answer, Assistant

app = FastAPI(title="Guichet des règlements", version=__version__)


class Question(BaseModel):
    question: str = Field(min_length=3, max_length=500)


@lru_cache(maxsize=1)
def _build_assistant() -> Assistant:
    """Construit l'assistant une seule fois (modèle d'embeddings et index chargés au 1er appel)."""
    from qdrant_client import QdrantClient

    from policy_help_desk.bm25 import BM25Index
    from policy_help_desk.embeddings import FastEmbedEmbedder
    from policy_help_desk.hybrid import HybridRetriever
    from policy_help_desk.index import DenseIndex
    from policy_help_desk.ingest import read_chunks
    from policy_help_desk.llm import make_provider
    from policy_help_desk.rag import Retriever

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
        from policy_help_desk.rerank import FastEmbedReranker, RerankingRetriever

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
