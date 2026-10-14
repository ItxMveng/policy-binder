"""Évalue l'assistant sur eval/questions.jsonl et écrit les résultats dans eval/results/.

Usage : uv run python scripts/run_eval.py <nom-du-run> [--limit N]
Prérequis : index construit (scripts/build_index.py) et LLM_API_KEY dans .env.
Le juge (qwen/qwen3.8-27b) est un autre modèle que celui qui répond (openai/gpt-oss-120b),
pour éviter qu'un modèle note ses propres réponses.
"""

import argparse
import json
import time
from datetime import UTC, datetime
from pathlib import Path

from policy_binder.bm25 import BM25Index
from policy_binder.config import get_settings
from policy_binder.embeddings import FastEmbedEmbedder
from policy_binder.evalset import load_questions
from policy_binder.evaluation import QuestionResult, score, summarize
from policy_binder.hybrid import HybridRetriever
from policy_binder.index import DenseIndex, make_qdrant_client
from policy_binder.ingest import read_chunks
from policy_binder.llm import make_provider
from policy_binder.rag import Assistant, Retriever
from policy_binder.rerank import DEFAULT_RERANKER, FastEmbedReranker, RerankingRetriever

JUDGE_MODEL = "qwen/qwen3.8-27b"
# Tarif public Groq de openai/gpt-oss-120b, relevé le 2026-10-12 sur
# https://console.groq.com/docs/model/openai/gpt-oss-120b (le coût réel est nul : offre gratuite).
PRICE_IN_PER_M = 0.15
PRICE_OUT_PER_M = 0.60
TOKENS_PER_MINUTE = 8000  # limite de l'offre gratuite : on espace les appels pour éviter les 429


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("name")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--retrieval", choices=["dense", "hybride"], default="dense")
    parser.add_argument("--rerank", action="store_true", help="reranker sur 20 candidats")
    parser.add_argument("--min-score", type=float, default=None, help="seuil d'abstention")
    parser.add_argument("--subset", type=Path, default=None, help="fichier d'identifiants")
    parser.add_argument("--rerank-candidates", type=int, default=None)
    parser.add_argument("--rerank-max-chars", type=int, default=None, help="0 = passage entier")
    args = parser.parse_args()

    settings = get_settings()
    if args.rerank_candidates is not None:
        settings.rerank_candidates = args.rerank_candidates
    if args.rerank_max_chars is not None:
        settings.rerank_max_chars = args.rerank_max_chars or None
    key = settings.llm_api_key.get_secret_value() if settings.llm_api_key else None
    questions = load_questions(settings.data_dir.parent / "eval" / "questions.jsonl")
    if args.subset is not None:
        lines = args.subset.read_text(encoding="utf-8").splitlines()
        wanted = {line.strip() for line in lines if line.strip() and not line.startswith("#")}
        questions = [q for q in questions if q.id in wanted]
    questions = questions[: args.limit]
    client = make_qdrant_client(settings)
    retriever: Retriever = DenseIndex(client, FastEmbedEmbedder())
    if args.retrieval == "hybride":
        chunks = read_chunks(settings.data_dir / "processed" / "chunks.jsonl")
        retriever = HybridRetriever(retriever, BM25Index(chunks))
    if args.rerank:
        retriever = RerankingRetriever(
            retriever, FastEmbedReranker(), settings.rerank_candidates, settings.rerank_max_chars
        )
    assistant = Assistant(
        retriever,
        make_provider(settings.llm_provider, settings.llm_model, key),
        k=settings.top_k,
        min_score=args.min_score,
    )
    judge_llm = make_provider(settings.llm_provider, JUDGE_MODEL, key)

    out_dir = settings.data_dir.parent / "eval" / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    details_path = out_dir / f"{args.name}-details.jsonl"
    # Reprise : les questions déjà évaluées (fichier écrit au fil de l'eau) ne sont pas refaites.
    results = []
    if details_path.exists():
        lines = details_path.read_text(encoding="utf-8").splitlines()
        results = [QuestionResult.model_validate_json(line) for line in lines if line.strip()]
    done = {r.id for r in results}

    with details_path.open("a", encoding="utf-8") as details:
        for question in questions:
            if question.id in done:
                continue
            started = time.perf_counter()
            answer = assistant.answer(question.question)
            result = score(question, answer, judge_llm)
            results.append(result)
            details.write(result.model_dump_json() + "\n")
            details.flush()
            print(f"{result.id}  {result.verdict:<11} {result.latency_ms:7.0f} ms", flush=True)
            tokens = answer.input_tokens + answer.output_tokens
            pause = tokens / TOKENS_PER_MINUTE * 60 - (time.perf_counter() - started)
            if pause > 0:
                time.sleep(pause)
    client.close()

    summary = summarize(results, PRICE_IN_PER_M, PRICE_OUT_PER_M)
    report = {
        "run": args.name,
        "date": datetime.now(UTC).isoformat(timespec="seconds"),
        "questions": len(results),
        "configuration": {
            "retrieval": args.retrieval,
            "reranker": (
                f"{DEFAULT_RERANKER} ({settings.rerank_candidates} candidats, "
                f"{settings.rerank_max_chars} car.)"
                if args.rerank
                else None
            ),
            "seuil_abstention": args.min_score,
            "embeddings": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
            "top_k": settings.top_k,
            "llm": f"{settings.llm_provider}:{settings.llm_model}",
            "juge": f"{settings.llm_provider}:{JUDGE_MODEL}",
        },
        "resultats": summary.model_dump(),
    }
    (out_dir / f"{args.name}.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report["resultats"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
