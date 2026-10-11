"""Construit l'index dense local (data/index/qdrant) à partir de data/processed/chunks.jsonl."""

import time

from qdrant_client import QdrantClient

from studeria_assistant.config import get_settings
from studeria_assistant.embeddings import FastEmbedEmbedder
from studeria_assistant.index import DenseIndex
from studeria_assistant.ingest import read_chunks


def main() -> None:
    settings = get_settings()
    chunks = read_chunks(settings.data_dir / "processed" / "chunks.jsonl")
    client = QdrantClient(path=str(settings.data_dir / "index" / "qdrant"))
    start = time.perf_counter()
    DenseIndex(client, FastEmbedEmbedder()).build(chunks)
    print(f"{len(chunks)} passages indexés en {time.perf_counter() - start:.1f} s")
    client.close()


if __name__ == "__main__":
    main()
