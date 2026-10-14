"""Compare la recherche seule (sans LLM, donc gratuite) : dense, BM25 et hybride (RRF).

Usage : uv run python scripts/eval_retrieval.py
Écrit eval/results/retrieval-comparison.json : part des 40 questions avec réponse dont la page
(ou le document) attendue figure parmi les k premiers passages, pour k = 1, 3, 5, 10.
"""

import json
import time

from policy_binder.bm25 import BM25Index
from policy_binder.config import get_settings
from policy_binder.embeddings import FastEmbedEmbedder
from policy_binder.evalset import load_questions
from policy_binder.evaluation import hit_at_k, wilson
from policy_binder.hybrid import HybridRetriever, Searcher
from policy_binder.index import DenseIndex, make_qdrant_client
from policy_binder.ingest import read_chunks
from policy_binder.rerank import FastEmbedReranker, RerankingRetriever

KS = (1, 3, 5, 10)


def main() -> None:
    settings = get_settings()
    root = settings.data_dir.parent
    questions = [q for q in load_questions(root / "eval" / "questions.jsonl") if q.answerable]
    client = make_qdrant_client(settings)
    dense = DenseIndex(client, FastEmbedEmbedder())
    lexical = BM25Index(read_chunks(settings.data_dir / "processed" / "chunks.jsonl"))
    reranker = FastEmbedReranker()
    searchers: dict[str, Searcher] = {
        "dense": dense,
        "bm25": lexical,
        "hybride": HybridRetriever(dense, lexical),
        # Réglage complet (20 candidats, passages entiers) : plafond de qualité, trop lent sur CPU.
        "hybride+rerank complet": RerankingRetriever(HybridRetriever(dense, lexical), reranker),
        # Réglage retenu sur la calibration : 10 candidats, 400 premiers caractères.
        "hybride+rerank retenu": RerankingRetriever(
            HybridRetriever(dense, lexical),
            reranker,
            settings.rerank_candidates,
            settings.rerank_max_chars,
        ),
    }

    report: dict[str, dict[str, object]] = {}
    for name, searcher in searchers.items():
        started = time.perf_counter()
        rankings = [searcher.search(q.question, max(KS)) for q in questions]
        elapsed_ms = (time.perf_counter() - started) * 1000 / len(questions)
        entry: dict[str, object] = {"latence_moyenne_ms": round(elapsed_ms, 1)}
        for level in ("page", "document"):
            for k in KS:
                count = sum(
                    hit_at_k(q, r, k, level) for q, r in zip(questions, rankings, strict=True)
                )
                entry[f"{level}@{k}"] = wilson(count, len(questions)).model_dump()
        entry["pages_manquees@5"] = [
            q.id for q, r in zip(questions, rankings, strict=True) if not hit_at_k(q, r, 5)
        ]
        report[name] = entry
        print(f"{name:23} page@1 page@3 page@5 page@10 :", end=" ")
        print(" ".join(f"{entry[f'page@{k}']['value'] * 100:5.1f}%" for k in KS))  # type: ignore[index]
    client.close()
    out = root / "eval" / "results" / "retrieval-comparison.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
