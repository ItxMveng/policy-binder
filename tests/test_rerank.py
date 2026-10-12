from collections.abc import Sequence

from studeria_assistant.index import ScoredChunk
from studeria_assistant.ingest import Chunk
from studeria_assistant.rerank import RerankingRetriever


def _hit(chunk_id: str, text: str) -> ScoredChunk:
    return ScoredChunk(
        chunk=Chunk(id=chunk_id, source_id="doc", title="T", page=1, text=text), score=0.0
    )


class FixedSearcher:
    def __init__(self, hits: list[ScoredChunk]) -> None:
        self.hits = hits
        self.asked_k = 0

    def search(self, query: str, k: int = 5) -> list[ScoredChunk]:
        self.asked_k = k
        return self.hits[:k]


class KeywordReranker:
    """Faux cross-encoder : 1 point par mot de la question présent dans le passage."""

    def scores(self, query: str, texts: Sequence[str]) -> list[float]:
        words = set(query.lower().split())
        return [float(len(words & set(text.lower().split()))) for text in texts]


def test_reranker_reorders_candidates_and_returns_its_scores() -> None:
    base = FixedSearcher([_hit("a", "le jury délibère"), _hit("b", "durée du prêt de livres")])
    retriever = RerankingRetriever(base, KeywordReranker(), candidates=20)
    hits = retriever.search("durée prêt livres", k=1)
    assert base.asked_k == 20
    assert [hit.chunk.id for hit in hits] == ["b"]
    assert hits[0].score == 3.0


def test_reranker_handles_empty_candidates() -> None:
    assert RerankingRetriever(FixedSearcher([]), KeywordReranker()).search("q") == []


class RecordingReranker:
    def __init__(self) -> None:
        self.seen: list[str] = []

    def scores(self, query: str, texts: Sequence[str]) -> list[float]:
        self.seen = list(texts)
        return [0.0] * len(texts)


def test_max_chars_truncates_what_the_reranker_reads_only() -> None:
    reranker = RecordingReranker()
    base = FixedSearcher([_hit("a", "x" * 1000)])
    hits = RerankingRetriever(base, reranker, max_chars=400).search("q", k=1)
    assert len(reranker.seen[0]) == 400
    assert len(hits[0].chunk.text) == 1000  # le LLM reçoit le passage complet
