"""Recherche hybride : fusion des classements dense et BM25 par Reciprocal Rank Fusion (RRF)."""

from collections.abc import Sequence
from typing import Protocol

from policy_binder.index import ScoredChunk

RRF_K = 60  # constante de l'article d'origine (Cormack et al., 2009) : atténue l'écart entre rangs


class Searcher(Protocol):
    def search(self, query: str, k: int = 5) -> list[ScoredChunk]: ...


def reciprocal_rank_fusion(
    rankings: Sequence[list[ScoredChunk]], k: int, rrf_k: int = RRF_K
) -> list[ScoredChunk]:
    """Score RRF = somme de 1 / (rrf_k + rang) sur les classements où le passage apparaît.

    On fusionne des rangs, pas des scores : un score cosinus et un score BM25 ne sont pas
    comparables, alors que « 1er ici, 3e là » l'est toujours.
    """
    fused: dict[str, float] = {}
    chunks: dict[str, ScoredChunk] = {}
    for ranking in rankings:
        for rank, hit in enumerate(ranking, start=1):
            fused[hit.chunk.id] = fused.get(hit.chunk.id, 0.0) + 1.0 / (rrf_k + rank)
            chunks.setdefault(hit.chunk.id, hit)
    best = sorted(fused, key=lambda chunk_id: fused[chunk_id], reverse=True)[:k]
    return [ScoredChunk(chunk=chunks[chunk_id].chunk, score=fused[chunk_id]) for chunk_id in best]


class HybridRetriever:
    def __init__(self, dense: Searcher, lexical: Searcher, candidates: int = 20) -> None:
        self.dense = dense
        self.lexical = lexical
        self.candidates = candidates

    def search(self, query: str, k: int = 5) -> list[ScoredChunk]:
        rankings = [
            self.dense.search(query, self.candidates),
            self.lexical.search(query, self.candidates),
        ]
        return reciprocal_rank_fusion(rankings, k)
