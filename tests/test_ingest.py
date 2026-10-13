from pathlib import Path

from policy_binder.ingest import Chunk, chunk_pages, clean_text, read_chunks, split_text
from policy_binder.sources import Source

SOURCE = Source.model_validate(
    {
        "id": "charte",
        "title": "Charte de test",
        "institution": "Test",
        "kind": "charte",
        "url": "https://example.org/charte.pdf",
        "consulted_on": "2026-10-11",
    }
)


def test_clean_text_removes_dot_leaders_and_hyphenation() -> None:
    raw = "Procédure disciplinaire ........................ 8\nLes sanc-\ntions   encourues"
    cleaned = clean_text(raw)
    assert "...." not in cleaned
    assert "sanctions encourues" in cleaned


def test_split_respects_max_size_and_keeps_overlap() -> None:
    sentences = [f"Phrase numéro {i} qui décrit une règle." for i in range(60)]
    chunks = split_text(" ".join(sentences), max_chars=300, overlap=80)
    assert len(chunks) > 1
    assert all(len(chunk) <= 300 for chunk in chunks)
    first_tail = chunks[0].split(". ")[-1]
    assert first_tail.rstrip(".") in chunks[1]  # la dernière phrase est reprise


def test_split_cuts_oversized_unit() -> None:
    chunks = split_text("x" * 2500, max_chars=1000)
    assert [len(c) for c in chunks] == [1000, 1000, 500]


def test_chunks_keep_page_and_skip_tiny_fragments() -> None:
    long_page = "L'étudiant dispose de deux mois pour contester une décision. " * 5
    chunks = chunk_pages(SOURCE, [(1, "page 1/10"), (2, long_page)])
    assert {chunk.page for chunk in chunks} == {2}
    assert chunks[0].id == "charte-p2-c0"


def test_chunks_roundtrip_jsonl(tmp_path: Path) -> None:
    from policy_binder.ingest import write_chunks

    chunk = Chunk(id="a-p1-c0", source_id="a", title="A", page=1, text="Texte « accentué ».")
    path = tmp_path / "chunks.jsonl"
    write_chunks([chunk], path)
    assert read_chunks(path) == [chunk]
