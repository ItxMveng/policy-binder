from studeria_assistant.bm25 import BM25Index, tokenize
from studeria_assistant.hybrid import HybridRetriever, reciprocal_rank_fusion
from studeria_assistant.index import ScoredChunk
from studeria_assistant.ingest import Chunk


def _chunk(chunk_id: str, text: str) -> Chunk:
    return Chunk(id=chunk_id, source_id=chunk_id.split("-")[0], title="T", page=1, text=text)


CHUNKS = [
    _chunk(
        "examens-a", "Les étudiants doivent se présenter 15 minutes avant le début de l'épreuve."
    ),
    _chunk("examens-b", "Le jury comprend au moins trois membres."),
    _chunk("numerique-a", "Utilisez le réseau wifi eduroam dans l'université."),
]


def test_tokenize_folds_accents_and_drops_stopwords() -> None:
    assert tokenize("Le délai de l'Épreuve : 15 minutes") == ["delai", "epreuve", "15", "minutes"]


def test_bm25_finds_exact_terms_and_numbers() -> None:
    index = BM25Index(CHUNKS)
    assert index.search("combien de minutes avant l'épreuve ?", k=1)[0].chunk.id == "examens-a"
    assert index.search("eduroam", k=1)[0].chunk.id == "numerique-a"
    assert index.search("cantine", k=3) == []  # aucun terme commun : aucun résultat


def test_rare_terms_weigh_more_than_common_ones() -> None:
    index = BM25Index(CHUNKS)
    terms = tokenize("jury eduroam")
    assert index.score(terms, 1) > 0 and index.score(terms, 2) > 0
    assert index._idf["eduroam"] == index._idf["jury"]  # même fréquence documentaire


def _ranking(*ids: str) -> list[ScoredChunk]:
    return [ScoredChunk(chunk=_chunk(i, i), score=1.0) for i in ids]


def test_rrf_rewards_documents_ranked_well_in_both_lists() -> None:
    fused = reciprocal_rank_fusion([_ranking("a", "b", "c"), _ranking("c", "a", "d")], k=4)
    assert [hit.chunk.id for hit in fused][:2] == ["a", "c"]
    assert fused[0].score == 1 / 61 + 1 / 62


class FixedSearcher:
    def __init__(self, ranking: list[ScoredChunk]) -> None:
        self.ranking = ranking
        self.asked_k = 0

    def search(self, query: str, k: int = 5) -> list[ScoredChunk]:
        self.asked_k = k
        return self.ranking[:k]


def test_hybrid_asks_more_candidates_than_it_returns() -> None:
    dense, lexical = FixedSearcher(_ranking("a", "b")), FixedSearcher(_ranking("b", "c"))
    hits = HybridRetriever(dense, lexical, candidates=20).search("q", k=2)
    assert dense.asked_k == lexical.asked_k == 20
    assert [hit.chunk.id for hit in hits] == ["b", "a"]
