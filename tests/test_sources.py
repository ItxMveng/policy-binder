from pathlib import Path

import httpx
import pytest

from policy_binder.config import ROOT_DIR
from policy_binder.sources import Source, download_source, load_sources

SOURCES_FILE = ROOT_DIR / "data" / "sources.yaml"


def test_versioned_sources_are_valid() -> None:
    sources = load_sources(SOURCES_FILE)
    assert len(sources) >= 6
    assert all(source.url.scheme == "https" for source in sources)
    assert {s.institution.split(" ")[0] for s in sources} >= {"ENIB", "Université", "IMT"}


def test_duplicate_ids_are_rejected(tmp_path: Path) -> None:
    entry = (
        "  - {id: a, title: t, institution: i, kind: k, "
        "url: 'https://example.org/a.pdf', consulted_on: 2026-10-11}\n"
    )
    path = tmp_path / "sources.yaml"
    path.write_text("sources:\n" + entry + entry, encoding="utf-8")
    with pytest.raises(ValueError, match="en double"):
        load_sources(path)


def _source() -> Source:
    return Source.model_validate(
        {
            "id": "doc",
            "title": "Doc",
            "institution": "Test",
            "kind": "charte",
            "url": "https://example.org/doc.pdf",
            "consulted_on": "2026-10-11",
        }
    )


def test_download_writes_pdf(tmp_path: Path) -> None:
    transport = httpx.MockTransport(lambda request: httpx.Response(200, content=b"%PDF-1.7 ..."))
    with httpx.Client(transport=transport) as client:
        digest = download_source(client, _source(), tmp_path)
    assert (tmp_path / "doc.pdf").read_bytes().startswith(b"%PDF")
    assert len(digest) == 64


def test_download_rejects_html_error_page(tmp_path: Path) -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, content=b"<html>404</html>")
    )
    with httpx.Client(transport=transport) as client, pytest.raises(ValueError):
        download_source(client, _source(), tmp_path)
