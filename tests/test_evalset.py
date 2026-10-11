import pytest
from pydantic import ValidationError

from studeria_assistant.config import ROOT_DIR
from studeria_assistant.evalset import EvalQuestion, check_eval_set, load_questions
from studeria_assistant.sources import load_sources


def test_versioned_eval_set_is_coherent() -> None:
    questions = load_questions(ROOT_DIR / "eval" / "questions.jsonl")
    sources = load_sources(ROOT_DIR / "data" / "sources.yaml")
    assert check_eval_set(questions, sources) == []


def test_eval_set_covers_every_institution() -> None:
    questions = load_questions(ROOT_DIR / "eval" / "questions.jsonl")
    cited = {s.source_id.split("-")[0] for q in questions for s in q.expected_sources}
    assert {"bretagne", "enib", "ubo", "imt"} <= cited


def test_answerable_question_requires_reference_and_evidence() -> None:
    with pytest.raises(ValidationError):
        EvalQuestion.model_validate(
            {
                "id": "x",
                "question": "Q ?",
                "answerable": True,
                "reference_answer": None,
                "expected_sources": [],
                "evidence": None,
            }
        )


def test_out_of_corpus_question_has_no_source() -> None:
    with pytest.raises(ValidationError):
        EvalQuestion.model_validate(
            {
                "id": "h",
                "question": "Q ?",
                "answerable": False,
                "reference_answer": None,
                "expected_sources": [{"source_id": "ubo-charte-examens", "page": 3}],
                "evidence": None,
            }
        )
