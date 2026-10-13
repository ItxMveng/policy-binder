"""Index dense dans Qdrant (mode embarqué en local, Qdrant Cloud en production)."""

import uuid
from collections.abc import Sequence

from pydantic import BaseModel
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from policy_help_desk.embeddings import Embedder
from policy_help_desk.ingest import Chunk

COLLECTION = "passages"
BATCH_SIZE = 64


class ScoredChunk(BaseModel):
    chunk: Chunk
    score: float


def point_id(chunk_id: str) -> str:
    """Qdrant exige un entier ou un UUID : UUID dérivé de l'identifiant lisible, donc stable."""
    return str(uuid.uuid5(uuid.NAMESPACE_URL, chunk_id))


class DenseIndex:
    def __init__(
        self, client: QdrantClient, embedder: Embedder, collection: str = COLLECTION
    ) -> None:
        self.client = client
        self.embedder = embedder
        self.collection = collection

    def build(self, chunks: Sequence[Chunk]) -> None:
        """Recrée la collection : l'index reflète exactement le fichier de passages."""
        if self.client.collection_exists(self.collection):
            self.client.delete_collection(self.collection)
        self.client.create_collection(
            self.collection,
            vectors_config=VectorParams(size=self.embedder.dim, distance=Distance.COSINE),
        )
        for start in range(0, len(chunks), BATCH_SIZE):
            batch = chunks[start : start + BATCH_SIZE]
            vectors = self.embedder.embed_documents([chunk.text for chunk in batch])
            points = [
                PointStruct(id=point_id(chunk.id), vector=vector, payload=chunk.model_dump())
                for chunk, vector in zip(batch, vectors, strict=True)
            ]
            self.client.upsert(self.collection, points=points)

    def search(self, query: str, k: int = 5) -> list[ScoredChunk]:
        response = self.client.query_points(
            self.collection, query=self.embedder.embed_query(query), limit=k, with_payload=True
        )
        return [
            ScoredChunk(chunk=Chunk.model_validate(point.payload), score=point.score)
            for point in response.points
        ]
