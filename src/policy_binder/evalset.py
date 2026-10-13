"""Jeu d'évaluation versionné : eval/questions.jsonl (40 questions avec réponse, 20 hors corpus)."""

import json
from pathlib import Path

from pydantic import BaseModel, model_validator

from policy_binder.sources import Source


class ExpectedSource(BaseModel):
    source_id: str
    page: int


class EvalQuestion(BaseModel):
    id: str
    question: str
    answerable: bool
    reference_answer: str | None
    expected_sources: list[ExpectedSource]
    # Extrait exact (en minuscules) présent sur la page attendue : rend la référence vérifiable.
    evidence: str | None

    @model_validator(mode="after")
    def _coherent(self) -> "EvalQuestion":
        if self.answerable and not (
            self.reference_answer and self.expected_sources and self.evidence
        ):
            raise ValueError(f"{self.id} : réponse, source et extrait attendus")
        if not self.answerable and (self.reference_answer or self.expected_sources):
            raise ValueError(f"{self.id} : une question hors corpus n'a ni réponse ni source")
        return self


def load_questions(path: Path) -> list[EvalQuestion]:
    lines = path.read_text(encoding="utf-8").splitlines()
    return [EvalQuestion.model_validate(json.loads(line)) for line in lines if line.strip()]


def check_eval_set(questions: list[EvalQuestion], sources: list[Source]) -> list[str]:
    """Renvoie la liste des problèmes de cohérence (vide si le jeu est valide)."""
    problems: list[str] = []
    ids = [q.id for q in questions]
    if len(set(ids)) != len(ids):
        problems.append("identifiants en double")
    answerable = sum(q.answerable for q in questions)
    if (answerable, len(questions) - answerable) != (40, 20):
        problems.append(
            f"attendu 40 + 20 questions, trouvé {answerable} + {len(questions) - answerable}"
        )
    known = {source.id for source in sources}
    for question in questions:
        for expected in question.expected_sources:
            if expected.source_id not in known:
                problems.append(f"{question.id} : source inconnue {expected.source_id}")
    return problems
