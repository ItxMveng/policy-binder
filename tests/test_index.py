from qdrant_client import QdrantClient

from policy_binder.index import DenseIndex, point_id
from policy_binder.ingest import Chunk
from tests.conftest import HashingEmbedder

CHUNKS = [
    Chunk(
        id="examens-p3-c0",
        source_id="examens",
        title="Charte des examens",
        page=3,
        text="Toute fraude aux examens entraîne une procédure disciplinaire.",
    ),
    Chunk(
        id="numerique-p2-c0",
        source_id="numerique",
        title="Charte du numérique",
        page=2,
        text="Le mot de passe du compte informatique est strictement personnel.",
    ),
    Chunk(
        id="ia-p5-c1",
        source_id="ia",
        title="Charte IA",
        page=5,
        text="L'usage d'une IA générative doit être déclaré dans le rapport.",
    ),
]


def _index() -> DenseIndex:
    index = DenseIndex(QdrantClient(":memory:"), HashingEmbedder())
    index.build(CHUNKS)
    return index


def test_search_returns_most_similar_chunk_with_metadata() -> None:
    hits = _index().search("mot de passe informatique personnel", k=2)
    assert hits[0].chunk.id == "numerique-p2-c0"
    assert hits[0].chunk.page == 2
    assert hits[0].score >= hits[1].score


def test_build_twice_does_not_duplicate_points() -> None:
    index = _index()
    index.build(CHUNKS)
    assert index.client.count(index.collection).count == len(CHUNKS)


def test_point_id_is_stable() -> None:
    assert point_id("examens-p3-c0") == point_id("examens-p3-c0")
    assert point_id("examens-p3-c0") != point_id("examens-p3-c1")
