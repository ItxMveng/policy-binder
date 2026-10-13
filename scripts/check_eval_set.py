"""Vérifie que chaque extrait (evidence) figure bien sur la page attendue du PDF.

Usage : uv run python scripts/check_eval_set.py   (après scripts/download_sources.py)
"""

import sys

from policy_help_desk.config import get_settings
from policy_help_desk.evalset import check_eval_set, load_questions
from policy_help_desk.ingest import pdf_pages
from policy_help_desk.sources import load_sources, raw_pdf_path


def main() -> int:
    settings = get_settings()
    sources = load_sources(settings.data_dir / "sources.yaml")
    questions = load_questions(settings.data_dir.parent / "eval" / "questions.jsonl")
    problems = check_eval_set(questions, sources)

    pages: dict[tuple[str, int], str] = {}
    for source in sources:
        for number, text in pdf_pages(raw_pdf_path(settings.data_dir / "raw", source)):
            pages[(source.id, number)] = " ".join(text.lower().split())

    verified = 0
    for question in questions:
        if not question.answerable or question.evidence is None:
            continue
        found = any(
            question.evidence in pages.get((s.source_id, s.page), "")
            for s in question.expected_sources
        )
        if found:
            verified += 1
        else:
            problems.append(f"{question.id} : extrait introuvable sur la page attendue")

    answerable = sum(q.answerable for q in questions)
    print(f"{verified}/{answerable} extraits retrouvés sur la page attendue")
    for problem in problems:
        print(f"PROBLÈME  {problem}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
