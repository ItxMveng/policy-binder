"""Ingestion : PDF → texte page par page → passages (chunks) avec métadonnées."""

import json
import logging
import re
from collections.abc import Iterable, Iterator
from pathlib import Path

from pydantic import BaseModel
from pypdf import PdfReader

from studeria_assistant.sources import Source, raw_pdf_path

logging.getLogger("pypdf").setLevel(logging.ERROR)

MAX_CHARS = 1000
OVERLAP_CHARS = 150

_DOT_LEADER = re.compile(r"(?:\s?\.){4,}\s*\d*")  # « Titre ........ 9 » des sommaires
_HYPHEN_BREAK = re.compile(r"(\w)-\n(\w)")
_SPACES = re.compile(r"[ \t ]+")
_BLANK_LINES = re.compile(r"\n{3,}")
_UNIT_SPLIT = re.compile(r"(?<=[.;:!?])\s+|\n+")


class Chunk(BaseModel):
    id: str
    source_id: str
    title: str
    page: int  # numéro de page à partir de 1, comme dans un lecteur PDF
    text: str


def clean_text(text: str) -> str:
    text = _HYPHEN_BREAK.sub(r"\1\2", text)
    text = _DOT_LEADER.sub(" ", text)
    text = _SPACES.sub(" ", text)
    text = "\n".join(line.strip() for line in text.splitlines())
    return _BLANK_LINES.sub("\n\n", text).strip()


def split_text(text: str, max_chars: int = MAX_CHARS, overlap: int = OVERLAP_CHARS) -> list[str]:
    """Découpe en morceaux d'au plus max_chars, sur des fins de phrase ou de ligne.

    Les dernières unités d'un morceau (jusqu'à `overlap` caractères) sont reprises au début du
    suivant : une règle coupée à la frontière reste lisible en entier dans au moins un morceau.
    """
    units: list[str] = []
    for unit in (u.strip() for u in _UNIT_SPLIT.split(text)):
        while len(unit) > max_chars:  # unité géante (tableau aplati) : coupe dure
            units.append(unit[:max_chars])
            unit = unit[max_chars:]
        if unit:
            units.append(unit)

    chunks: list[str] = []
    current: list[str] = []
    for unit in units:
        if current and len(" ".join([*current, unit])) > max_chars:
            chunks.append(" ".join(current))
            tail: list[str] = []
            for previous in reversed(current):
                if len(" ".join([previous, *tail])) > overlap:
                    break
                tail.insert(0, previous)
            current = tail
        current.append(unit)
    if current:
        chunks.append(" ".join(current))
    return chunks


def pdf_pages(path: Path) -> Iterator[tuple[int, str]]:
    for number, page in enumerate(PdfReader(path).pages, start=1):
        yield number, clean_text(page.extract_text() or "")


def chunk_pages(source: Source, pages: Iterable[tuple[int, str]]) -> list[Chunk]:
    """Les morceaux ne traversent jamais une page : chaque citation renvoie à une page exacte."""
    chunks: list[Chunk] = []
    for page_number, text in pages:
        for index, piece in enumerate(split_text(text)):
            if len(piece) < 40:  # numéro de page, en-tête isolé : rien à citer
                continue
            chunks.append(
                Chunk(
                    id=f"{source.id}-p{page_number}-c{index}",
                    source_id=source.id,
                    title=source.title,
                    page=page_number,
                    text=piece,
                )
            )
    return chunks


def ingest_sources(sources: list[Source], raw_dir: Path) -> list[Chunk]:
    chunks: list[Chunk] = []
    for source in sources:
        chunks.extend(chunk_pages(source, pdf_pages(raw_pdf_path(raw_dir, source))))
    return chunks


def write_chunks(chunks: list[Chunk], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = (chunk.model_dump_json() for chunk in chunks)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def read_chunks(path: Path) -> list[Chunk]:
    lines = path.read_text(encoding="utf-8").splitlines()
    return [Chunk.model_validate(json.loads(line)) for line in lines if line.strip()]
