"""API HTTP de l'assistant."""

from functools import lru_cache
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from policy_binder import __version__
from policy_binder.config import get_settings
from policy_binder.rag import Answer, Assistant
from policy_binder.ratelimit import DemoLimiter, client_ip
from policy_binder.sources import load_sources
from policy_binder.tracing import Tracer

app = FastAPI(title="Le Classeur", version=__version__)
# Le front (Vite en local, Vercel en production) appelle l'API depuis une autre origine.
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


_settings = get_settings()
limiter = DemoLimiter(
    per_ip=_settings.rate_limit_per_ip,
    window_s=_settings.rate_limit_window_s,
    daily=_settings.daily_quota,
)


class Question(BaseModel):
    question: str = Field(min_length=3, max_length=500)


@lru_cache(maxsize=1)
def _build_assistant() -> Assistant:
    """Construit l'assistant une seule fois (modèle d'embeddings et index chargés au 1er appel)."""
    from policy_binder.bm25 import BM25Index
    from policy_binder.embeddings import FastEmbedEmbedder
    from policy_binder.hybrid import HybridRetriever
    from policy_binder.index import DenseIndex, make_qdrant_client
    from policy_binder.ingest import read_chunks
    from policy_binder.llm import make_provider
    from policy_binder.rag import Retriever

    settings = get_settings()
    key = settings.llm_api_key.get_secret_value() if settings.llm_api_key else None
    retriever: Retriever = DenseIndex(make_qdrant_client(settings), FastEmbedEmbedder())
    if settings.retrieval == "hybride":
        chunks = read_chunks(settings.data_dir / "processed" / "chunks.jsonl")
        retriever = HybridRetriever(retriever, BM25Index(chunks))
    min_score = None
    if settings.rerank:
        from policy_binder.rerank import FastEmbedReranker, RerankingRetriever

        retriever = RerankingRetriever(
            retriever, FastEmbedReranker(), settings.rerank_candidates, settings.rerank_max_chars
        )
        min_score = settings.min_score
    llm = make_provider(settings.llm_provider, settings.llm_model, key)
    return Assistant(retriever, llm, k=settings.top_k, min_score=min_score, tracer=_build_tracer())


def _build_tracer() -> Tracer | None:
    """Langfuse seulement si les deux clés sont configurées ; sinon aucune trace n'est envoyée."""
    settings = get_settings()
    if settings.langfuse_public_key is None or settings.langfuse_secret_key is None:
        return None
    from policy_binder.tracing import LangfuseTracer

    return LangfuseTracer(
        settings.langfuse_public_key,
        settings.langfuse_secret_key.get_secret_value(),
        settings.langfuse_host,
    )


def get_assistant() -> Assistant:
    if not get_settings().llm_ready:
        raise HTTPException(status_code=503, detail="LLM_API_KEY non configurée.")
    return _build_assistant()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "version": __version__}


class SourceInfo(BaseModel):
    id: str
    title: str
    institution: str
    url: str


@app.get("/sources")
def sources() -> list[SourceInfo]:
    """Documents du corpus avec leur URL officielle : le front en fait des liens « page N »."""
    return [
        SourceInfo(id=s.id, title=s.title, institution=s.institution, url=str(s.url))
        for s in load_sources(get_settings().data_dir / "sources.yaml")
    ]


@app.post("/ask")
def ask(
    payload: Question,
    request: Request,
    assistant: Annotated[Assistant, Depends(get_assistant)],
) -> Answer:
    peer = request.client.host if request.client else None
    refusal = limiter.check(client_ip(request.headers.get("x-forwarded-for"), peer))
    if refusal is not None:
        raise HTTPException(status_code=429, detail=refusal)
    return assistant.answer(payload.question)
