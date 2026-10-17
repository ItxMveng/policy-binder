"""Reranking : un cross-encoder relit chaque paire (question, passage) et reclasse les candidats.

La recherche (dense ou BM25) compare des représentations calculées séparément ; le cross-encoder lit
la question et le passage ensemble : plus précis, plus lent, donc appliqué à 20 candidats seulement.
"""

from collections.abc import Callable, Sequence
from typing import Protocol

from policy_binder.hybrid import Searcher
from policy_binder.index import ScoredChunk

DEFAULT_RERANKER = "BAAI/bge-reranker-v2-m3-int8"  # multilingue, Apache-2.0, 0,57 Go


class Reranker(Protocol):
    def scores(self, query: str, texts: Sequence[str]) -> list[float]: ...


class FastEmbedReranker:
    """Cross-encoder exécuté en local (ONNX, CPU), téléchargé au premier appel."""

    def __init__(self, model_name: str = DEFAULT_RERANKER) -> None:
        from fastembed.rerank.cross_encoder import TextCrossEncoder

        self._model = TextCrossEncoder(model_name=model_name)

    def scores(self, query: str, texts: Sequence[str]) -> list[float]:
        return [float(score) for score in self._model.rerank(query, list(texts))]


class RerankingRetriever:
    """Prend `candidates` passages au retriever de base et garde les k mieux notés par le reranker.

    Le score renvoyé est celui du reranker : c'est lui que compare le seuil d'abstention.
    """

    def __init__(
        self,
        base: Searcher,
        reranker: Reranker,
        candidates: int = 20,
        max_chars: int | None = None,
    ) -> None:
        self.base = base
        self.reranker = reranker
        self.candidates = candidates
        # Le coût du cross-encoder croît avec la longueur lue : on peut ne lui montrer que le début
        # de chaque passage. Le LLM reçoit toujours le passage complet.
        self.max_chars = max_chars

    def search(self, query: str, k: int = 5) -> list[ScoredChunk]:
        hits = self.base.search(query, self.candidates)
        if not hits:
            return []
        texts = [hit.chunk.text[: self.max_chars] for hit in hits]
        scores = self.reranker.scores(query, texts)
        ranked = sorted(zip(scores, hits, strict=True), key=lambda pair: pair[0], reverse=True)
        return [ScoredChunk(chunk=hit.chunk, score=score) for score, hit in ranked[:k]]

    def search_grouped(
        self, query: str, groups: Sequence[tuple[str, Callable[[str], bool]]]
    ) -> list[list[ScoredChunk]]:
        """Réserve des candidats à chaque groupe de sources, puis les reclasse en un seul passage.

        Pour une question sur plusieurs établissements : sans réserve, les 20 candidats peuvent
        tous venir d'un seul établissement, et la bonne page d'un autre n'est jamais relue. Chaque
        groupe a sa propre requête de première étape (le sujet et le nom de l'établissement) ; le
        reranker note ensuite le sujet seul. Le coût reste celui d'une question simple
        (`candidates` passages relus au total).
        """
        par_groupe = max(1, self.candidates // len(groups))
        pools = [
            [
                hit
                for hit in self.base.search(first_stage, self.candidates * 3)
                if keep(hit.chunk.source_id)
            ][:par_groupe]
            for first_stage, keep in groups
        ]
        unique = {hit.chunk.id: hit.chunk for pool in pools for hit in pool}
        if not unique:
            return [[] for _ in groups]
        texts = [chunk.text[: self.max_chars] for chunk in unique.values()]
        scores = dict(zip(unique, self.reranker.scores(query, texts), strict=True))
        return [
            sorted(
                (ScoredChunk(chunk=hit.chunk, score=scores[hit.chunk.id]) for hit in pool),
                key=lambda hit: hit.score,
                reverse=True,
            )
            for pool in pools
        ]
