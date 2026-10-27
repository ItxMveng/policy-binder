"""Convertit les PDF de data/raw/ en passages : data/processed/chunks.jsonl.

Usage : uv run python scripts/ingest.py [--ignorer-absents]   (après scripts/download_sources.py)
--ignorer-absents : un PDF absent (téléchargement en échec) est signalé et ignoré.
"""

import sys
from collections import Counter

from policy_binder.config import get_settings
from policy_binder.ingest import ingest_sources, write_chunks
from policy_binder.sources import load_sources


def main() -> None:
    settings = get_settings()
    sources = load_sources(settings.data_dir / "sources.yaml")
    skip_missing = "--ignorer-absents" in sys.argv[1:]
    chunks = ingest_sources(sources, settings.data_dir / "raw", skip_missing=skip_missing)
    write_chunks(chunks, settings.data_dir / "processed" / "chunks.jsonl")
    per_source = Counter(chunk.source_id for chunk in chunks)
    for source in sources:
        absent = "  (PDF absent : ignoré)" if per_source[source.id] == 0 else ""
        print(f"{per_source[source.id]:5d}  {source.id}{absent}")
    print(f"{len(chunks):5d}  passages au total")


if __name__ == "__main__":
    main()
