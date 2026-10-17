from pathlib import Path

import pytest

from policy_binder.etablissements import ETABLISSEMENTS, etablissements_cites, sans_etablissements
from policy_binder.sources import load_sources


@pytest.mark.parametrize(
    ("question", "sujet"),
    [
        (
            "Quelle est la moyenne pour que je réussisse mon année scolaire à l'UBO et à l'ENIB ?",
            "Quelle est la moyenne pour que je réussisse mon année scolaire ?",
        ),
        ("Peut-on vapoter à IMT Atlantique ou à l'ENIB ?", "Peut-on vapoter ?"),
        (
            "Règles d'examen de l'Université de Brest, de Bretagne INP et d'IMT ?",
            "Règles d'examen ?",
        ),
    ],
)
def test_subject_without_institutions(question: str, sujet: str) -> None:
    assert sans_etablissements(question) == sujet


def test_question_restricted_to_one_institution() -> None:
    question = "Peut-on vapoter dans les locaux de l'ENIB et d'IMT Atlantique ?"
    enib, imt = etablissements_cites(question)
    assert sans_etablissements(question, enib) == "Peut-on vapoter dans les locaux de l'ENIB ?"
    assert (
        sans_etablissements(question, imt)
        == "Peut-on vapoter dans les locaux et d'IMT Atlantique ?"
    )


def test_institutions_are_found_in_corpus_order() -> None:
    noms = [e.nom for e in etablissements_cites("À l'ENIB, à IMT Atlantique et à l'UBO ?")]
    assert noms == [e.nom for e in ETABLISSEMENTS]
    assert etablissements_cites("Peut-on vapoter sur le campus ?") == []


def test_every_source_belongs_to_exactly_one_institution() -> None:
    sources_yaml = Path(__file__).resolve().parents[1] / "data" / "sources.yaml"
    for source in load_sources(sources_yaml):
        owners = [e.nom for e in ETABLISSEMENTS if e.possede(source.id)]
        assert len(owners) == 1, source.id
