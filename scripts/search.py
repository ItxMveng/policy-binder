"""Recherche dans l'index local. Usage : uv run python scripts/search.py "ma question" [k]"""

import sys

from policy_binder.config import get_settings
from policy_binder.embeddings import FastEmbedEmbedder
from policy_binder.index import DenseIndex, make_qdrant_client


def main() -> None:
    question = sys.argv[1]
    k = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    client = make_qdrant_client(get_settings())
    for hit in DenseIndex(client, FastEmbedEmbedder()).search(question, k):
        print(f"{hit.score:.3f}  {hit.chunk.source_id} p.{hit.chunk.page}")
        print(f"       {hit.chunk.text[:200]}")
    client.close()


if __name__ == "__main__":
    main()
