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

from qdrant_client import QdrantClient

from studeria_assistant.bm25 import BM25Index
from studeria_assistant.config import get_settings
from studeria_assistant.embeddings import FastEmbedEmbedder
from studeria_assistant.evalset import load_questions
from studeria_assistant.evaluation import QuestionResult, score, summarize
from studeria_assistant.hybrid import HybridRetriever
from studeria_assistant.index import DenseIndex
from studeria_assistant.ingest import read_chunks
from studeria_assistant.llm import make_provider
from studeria_assistant.rag import Assistant, Retriever

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
    args = parser.parse_args()

    settings = get_settings()
    key = settings.llm_api_key.get_secret_value() if settings.llm_api_key else None
    questions = load_questions(settings.data_dir.parent / "eval" / "questions.jsonl")[: args.limit]
    client = QdrantClient(path=str(settings.qdrant_path))
    retriever: Retriever = DenseIndex(client, FastEmbedEmbedder())
    if args.retrieval == "hybride":
        chunks = read_chunks(settings.data_dir / "processed" / "chunks.jsonl")
        retriever = HybridRetriever(retriever, BM25Index(chunks))
    assistant = Assistant(
        retriever,
        make_provider(settings.llm_provider, settings.llm_model, key),
        k=settings.top_k,
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
