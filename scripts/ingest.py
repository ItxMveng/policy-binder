"""Convertit les PDF de data/raw/ en passages : data/processed/chunks.jsonl.

Usage : uv run python scripts/ingest.py   (après scripts/download_sources.py)
"""

from collections import Counter

from studeria_assistant.config import get_settings
from studeria_assistant.ingest import ingest_sources, write_chunks
from studeria_assistant.sources import load_sources


def main() -> None:
    settings = get_settings()
    sources = load_sources(settings.data_dir / "sources.yaml")
    chunks = ingest_sources(sources, settings.data_dir / "raw")
    write_chunks(chunks, settings.data_dir / "processed" / "chunks.jsonl")
    per_source = Counter(chunk.source_id for chunk in chunks)
    for source in sources:
        print(f"{per_source[source.id]:5d}  {source.id}")
    print(f"{len(chunks):5d}  passages au total")


if __name__ == "__main__":
    main()
