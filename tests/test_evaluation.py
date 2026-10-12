import pytest

from studeria_assistant.evalset import EvalQuestion
from studeria_assistant.evaluation import (
    QuestionResult,
    parse_verdict,
    percentile,
    score,
    summarize,
    wilson,
)
from studeria_assistant.llm import LLMResponse
from studeria_assistant.rag import Answer, Citation
from tests.test_rag import PASSAGES

QUESTION = EvalQuestion.model_validate(
    {
        "id": "q1",
        "question": "Puis-je utiliser une IA ?",
        "answerable": True,
        "reference_answer": "Il faut déclarer l'usage.",
        "expected_sources": [{"source_id": "ia", "page": 11}],
        "evidence": "déclaré",
    }
)
OUT_OF_CORPUS = EvalQuestion.model_validate(
    {
        "id": "h1",
        "question": "Prix du repas ?",
        "answerable": False,
        "reference_answer": None,
        "expected_sources": [],
        "evidence": None,
    }
)


class FakeJudge:
    def __init__(self, text: str) -> None:
        self.text = text

    def complete(self, system: str, user: str) -> LLMResponse:
        return LLMResponse(text=self.text, model="juge", input_tokens=0, output_tokens=0)


def _answer(text: str, abstained: bool, cited: bool) -> Answer:
    citations = (
        [Citation(number=1, chunk_id="ia-p11-c0", source_id="ia", title="Charte IA", page=11)]
        if cited
        else []
    )
    return Answer(
        question="?",
        text=text,
        abstained=abstained,
        citations=citations,
        retrieved=PASSAGES,
        latency_ms=100.0,
        input_tokens=1000,
        output_tokens=100,
    )


def test_wilson_interval_contains_proportion_and_is_wide_on_small_samples() -> None:
    rate = wilson(30, 40)
    assert rate.low < 0.75 < rate.high
    assert rate.high - rate.low > 0.2  # 40 questions : incertitude d'environ ±13 points
    assert wilson(0, 0).value == 0.0


def test_percentile_interpolates() -> None:
    assert percentile([1.0, 2.0, 3.0, 4.0], 0.5) == pytest.approx(2.5)
    assert percentile([10.0] * 5, 0.95) == 10.0


def test_parse_verdict_reads_json_and_is_strict_otherwise() -> None:
    assert parse_verdict('```json\n{"verdict": "Correct", "justification": "ok"}\n```') == (
        "correct",
        "ok",
    )
    assert parse_verdict("je pense que c'est bon")[0] == "incorrect"


def test_score_answerable_question_with_judge() -> None:
    judge = FakeJudge('{"verdict": "correct", "justification": "même fait"}')
    result = score(QUESTION, _answer("Déclarez-le [1].", False, True), judge)
    assert result.verdict == "correct"
    assert result.context_hit_page and result.context_hit_document and result.citation_ok


def test_score_abstention_and_out_of_corpus() -> None:
    judge = FakeJudge("ne doit pas être appelé")
    assert score(QUESTION, _answer("Je ne trouve pas", True, False), judge).verdict == "abstention"
    assert score(OUT_OF_CORPUS, _answer("Je ne trouve pas", True, False), judge).abstained


def _result(answerable: bool, verdict: str, abstained: bool) -> QuestionResult:
    return QuestionResult(
        id="x",
        answerable=answerable,
        answer="",
        abstained=abstained,
        verdict=verdict,  # type: ignore[arg-type]
        context_hit_page=True,
        context_hit_document=True,
        citation_ok=not abstained,
        latency_ms=200.0,
        input_tokens=2000,
        output_tokens=500,
    )


def test_summarize_rates_and_cost() -> None:
    results = [
        _result(True, "correct", False),
        _result(True, "abstention", True),
        _result(False, "hors_corpus", True),
        _result(False, "hors_corpus", False),
    ]
    summary = summarize(results, price_in_per_m=0.15, price_out_per_m=0.60)
    assert summary.exactitude.value == 0.5
    assert summary.refus_injustifies.value == 0.5
    assert summary.abstention_correcte.value == 0.5
    assert summary.citations_correctes.total == 1
    # 1 000 × (2 000 × 0,15 + 500 × 0,60) / 1e6 = 0,60 $
    assert summary.cout_1000_questions_usd == pytest.approx(0.60)
