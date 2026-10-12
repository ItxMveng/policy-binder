"""Calibre le seuil d'abstention sur eval/calibration.jsonl (24 questions hors jeu de test).

Usage : uv run python scripts/calibrate_threshold.py
Aucun appel au LLM : seuls la recherche hybride et le reranker sont utilisés.
Écrit eval/results/calibration-<candidats>-<caractères>.json (scores, seuil, effet).
"""

import argparse
import json

from qdrant_client import QdrantClient

from studeria_assistant.bm25 import BM25Index
from studeria_assistant.config import get_settings
from studeria_assistant.embeddings import FastEmbedEmbedder
from studeria_assistant.evalset import load_questions
from studeria_assistant.evaluation import choose_threshold
from studeria_assistant.hybrid import HybridRetriever
from studeria_assistant.index import DenseIndex
from studeria_assistant.ingest import read_chunks
from studeria_assistant.rerank import DEFAULT_RERANKER, FastEmbedReranker, RerankingRetriever


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rerank-candidates", type=int, default=None)
    parser.add_argument("--rerank-max-chars", type=int, default=None, help="0 = passage entier")
    args = parser.parse_args()
    settings = get_settings()
    if args.rerank_candidates is not None:
        settings.rerank_candidates = args.rerank_candidates
    if args.rerank_max_chars is not None:
        settings.rerank_max_chars = args.rerank_max_chars or None
    root = settings.data_dir.parent
    questions = load_questions(root / "eval" / "calibration.jsonl")
    client = QdrantClient(path=str(settings.qdrant_path))
    hybrid = HybridRetriever(
        DenseIndex(client, FastEmbedEmbedder()),
        BM25Index(read_chunks(settings.data_dir / "processed" / "chunks.jsonl")),
    )
    retriever = RerankingRetriever(
        hybrid, FastEmbedReranker(), settings.rerank_candidates, settings.rerank_max_chars
    )

    rows: list[tuple[str, bool, float]] = []
    for question in questions:
        top = retriever.search(question.question, k=1)
        score = top[0].score if top else float("-inf")
        rows.append((question.id, question.answerable, score))
        label = "réponse" if question.answerable else "hors   "
        print(f"{question.id}  {label}  {score:7.3f}")
    client.close()

    threshold = choose_threshold([score for _, answerable, score in rows if answerable])
    out_of_corpus = [score for _, answerable, score in rows if not answerable]
    filtered = sum(score < threshold for score in out_of_corpus)
    report = {
        "reranker": DEFAULT_RERANKER,
        "candidats": settings.rerank_candidates,
        "max_chars": settings.rerank_max_chars,
        "regle": "plus haut seuil ne refusant aucune question de calibration avec réponse",
        "seuil": threshold,
        "hors_corpus_filtres_avant_llm": f"{filtered}/{len(out_of_corpus)}",
        "scores": [{"id": i, "answerable": a, "score": sc} for i, a, sc in rows],
    }
    suffix = f"{settings.rerank_candidates}-{settings.rerank_max_chars or 'complet'}"
    out = root / "eval" / "results" / f"calibration-{suffix}.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"seuil = {threshold:.3f} ; hors corpus filtrés : {filtered}/{len(out_of_corpus)}")


if __name__ == "__main__":
    main()
