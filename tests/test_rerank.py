from collections.abc import Sequence

from policy_binder.index import ScoredChunk
from policy_binder.ingest import Chunk
from policy_binder.rerank import RerankingRetriever


def _hit(chunk_id: str, text: str) -> ScoredChunk:
    return ScoredChunk(
        chunk=Chunk(id=chunk_id, source_id="doc", title="T", page=1, text=text), score=0.0
    )


class FixedSearcher:
    def __init__(self, hits: list[ScoredChunk]) -> None:
        self.hits = hits
        self.asked_k = 0
        self.queries: list[str] = []

    def search(self, query: str, k: int = 5) -> list[ScoredChunk]:
        self.asked_k = k
        self.queries.append(query)
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


def _sourced(chunk_id: str, source_id: str, text: str) -> ScoredChunk:
    chunk = Chunk(id=chunk_id, source_id=source_id, title="T", page=1, text=text)
    return ScoredChunk(chunk=chunk, score=0.0)


def test_grouped_search_reserves_candidates_for_each_group() -> None:
    # Sans réserve, les 4 premiers candidats viennent tous de l'UBO et la page ENIB n'est pas relue.
    hits = [_sourced(f"u{i}", "ubo-x", "vapoter interdit") for i in range(6)]
    hits.append(_sourced("e1", "enib-y", "cigarette électronique interdite vapoter"))
    base = FixedSearcher(hits)
    retriever = RerankingRetriever(base, KeywordReranker(), candidates=4)
    ubo, enib = retriever.search_grouped(
        "vapoter interdit",
        [
            ("vapoter UBO", lambda s: s.startswith("ubo-")),
            ("vapoter ENIB", lambda s: s.startswith("enib-")),
        ],
    )
    assert base.asked_k == 12 and base.queries == ["vapoter UBO", "vapoter ENIB"]
    assert [h.chunk.id for h in ubo] == ["u0", "u1"]
    assert [h.chunk.id for h in enib] == ["e1"] and enib[0].score == 1.0
