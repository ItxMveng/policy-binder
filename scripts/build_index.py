"""Construit l'index dense local (data/index/qdrant) à partir de data/processed/chunks.jsonl."""

import time

from qdrant_client import QdrantClient

from policy_binder.config import get_settings
from policy_binder.embeddings import FastEmbedEmbedder
from policy_binder.index import DenseIndex
from policy_binder.ingest import read_chunks


def main() -> None:
    settings = get_settings()
    chunks = read_chunks(settings.data_dir / "processed" / "chunks.jsonl")
    client = QdrantClient(path=str(settings.qdrant_path))
    start = time.perf_counter()
    DenseIndex(client, FastEmbedEmbedder()).build(chunks)
    print(f"{len(chunks)} passages indexés en {time.perf_counter() - start:.1f} s")
    client.close()


if __name__ == "__main__":
    main()
