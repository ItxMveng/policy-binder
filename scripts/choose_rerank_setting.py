"""Choisit le réglage du reranker sur le jeu de CALIBRATION (jamais sur le jeu de test).

Règle fixée avant la mesure : parmi les réglages dont la latence moyenne de recherche reste sous
BUDGET_MS, garder le plus rapide qui atteint la meilleure part de pages attendues dans le top 5.
Usage : uv run python scripts/choose_rerank_setting.py → eval/results/rerank-setting.json
"""

import json
import time

from qdrant_client import QdrantClient

from policy_help_desk.bm25 import BM25Index
from policy_help_desk.config import get_settings
from policy_help_desk.embeddings import FastEmbedEmbedder
from policy_help_desk.evalset import load_questions
from policy_help_desk.evaluation import hit_at_k
from policy_help_desk.hybrid import HybridRetriever
from policy_help_desk.index import DenseIndex
from policy_help_desk.ingest import read_chunks
from policy_help_desk.rerank import FastEmbedReranker, RerankingRetriever

BUDGET_MS = 3000
SETTINGS = [(20, None), (10, None), (20, 600), (10, 600), (10, 400)]


def main() -> None:
    settings = get_settings()
    root = settings.data_dir.parent
    questions = [q for q in load_questions(root / "eval" / "calibration.jsonl") if q.answerable]
    client = QdrantClient(path=str(settings.qdrant_path))
    hybrid = HybridRetriever(
        DenseIndex(client, FastEmbedEmbedder()),
        BM25Index(read_chunks(settings.data_dir / "processed" / "chunks.jsonl")),
    )
    reranker = FastEmbedReranker()

    rows = []
    for candidates, max_chars in SETTINGS:
        retriever = RerankingRetriever(hybrid, reranker, candidates, max_chars)
        started = time.perf_counter()
        rankings = [retriever.search(q.question, 5) for q in questions]
        latency = (time.perf_counter() - started) * 1000 / len(questions)
        hits1 = sum(hit_at_k(q, r, 1) for q, r in zip(questions, rankings, strict=True))
        hits5 = sum(hit_at_k(q, r, 5) for q, r in zip(questions, rankings, strict=True))
        rows.append(
            {
                "candidats": candidates,
                "max_chars": max_chars,
                "latence_ms": round(latency),
                "page@1": f"{hits1}/{len(questions)}",
                "page@5": f"{hits5}/{len(questions)}",
                "_hits5": hits5,
            }
        )
        print(f"{candidates:3} candidats, max_chars={max_chars}: {latency:6.0f} ms ", end="")
        print(f"page@1 {hits1}/{len(questions)}  page@5 {hits5}/{len(questions)}")
    client.close()

    in_budget = [r for r in rows if r["latence_ms"] <= BUDGET_MS]  # type: ignore[operator]
    best = max(r["_hits5"] for r in in_budget)  # type: ignore[type-var]
    chosen = min(
        (r for r in in_budget if r["_hits5"] == best),
        key=lambda r: r["latence_ms"],  # type: ignore[arg-type,return-value]
    )
    for row in rows:
        row.pop("_hits5")
    report = {"budget_ms": BUDGET_MS, "regle": __doc__.split("\n")[2], "reglages": rows}
    report["retenu"] = {"candidats": chosen["candidats"], "max_chars": chosen["max_chars"]}
    out = root / "eval" / "results" / "rerank-setting.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("retenu :", report["retenu"])


if __name__ == "__main__":
    main()
