"""Télécharge les PDF listés dans data/sources.yaml vers data/raw/ (non versionné).

Usage : uv run python scripts/download_sources.py
"""

import json
import sys

from studeria_assistant.config import get_settings
from studeria_assistant.sources import download_source, load_sources, make_client


def main() -> int:
    settings = get_settings()
    sources = load_sources(settings.data_dir / "sources.yaml")
    raw_dir = settings.data_dir / "raw"
    manifest: dict[str, str] = {}
    failures = 0
    with make_client() as client:
        for source in sources:
            try:
                manifest[source.id] = download_source(client, source, raw_dir)
                print(f"ok      {source.id}")
            except Exception as error:  # on continue pour lister toutes les sources en échec
                failures += 1
                print(f"ÉCHEC   {source.id} : {error}")
    (raw_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"{len(manifest)} téléchargés, {failures} en échec")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
