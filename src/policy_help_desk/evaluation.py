"""Évaluation de l'assistant sur le jeu versionné : métriques, juge LLM, incertitude."""

import json
import math
import re
from typing import Literal

from pydantic import BaseModel

from policy_help_desk.evalset import EvalQuestion
from policy_help_desk.index import ScoredChunk
from policy_help_desk.llm import LLMProvider
from policy_help_desk.rag import Answer

Verdict = Literal["correct", "partiel", "incorrect", "abstention", "hors_corpus"]

JUDGE_SYSTEM = """Tu évalues la réponse d'un assistant documentaire par rapport à une réponse \
de référence rédigée à partir des documents officiels.
- "correct" : la réponse contient les faits essentiels de la référence et ne la contredit pas.
- "partiel" : la réponse est juste mais il manque un fait essentiel de la référence.
- "incorrect" : la réponse contredit la référence, invente un fait, ou ne répond pas à la question.
Réponds uniquement par un objet JSON : {"verdict": "correct|partiel|incorrect", "justification": \
"une phrase"}"""

_JSON_OBJECT = re.compile(r"\{.*\}", re.DOTALL)


class QuestionResult(BaseModel):
    id: str
    answerable: bool
    answer: str
    abstained: bool
    verdict: Verdict
    justification: str = ""
    context_hit_page: bool  # (document, page) attendus parmi les passages récupérés
    context_hit_document: bool  # document attendu parmi les passages récupérés
    citation_ok: bool  # au moins une citation pointe vers (document, page) attendus
    latency_ms: float
    input_tokens: int
    output_tokens: int


class Rate(BaseModel):
    """Proportion avec intervalle de Wilson à 95 % : indispensable sur un petit échantillon."""

    count: int
    total: int
    value: float
    low: float
    high: float


def wilson(count: int, total: int, z: float = 1.96) -> Rate:
    if total == 0:
        return Rate(count=0, total=0, value=0.0, low=0.0, high=0.0)
    p = count / total
    denominator = 1 + z * z / total
    centre = (p + z * z / (2 * total)) / denominator
    margin = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / denominator
    return Rate(
        count=count,
        total=total,
        value=p,
        low=max(0.0, centre - margin),
        high=min(1.0, centre + margin),
    )


def percentile(values: list[float], q: float) -> float:
    """Percentile par interpolation linéaire (même convention que numpy par défaut)."""
    if not values:
        return 0.0
    ordered = sorted(values)
    position = (len(ordered) - 1) * q
    lower = math.floor(position)
    upper = math.ceil(position)
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def parse_verdict(text: str) -> tuple[Verdict, str]:
    """Lit la sortie du juge ; toute sortie illisible compte comme « incorrect » (prudence)."""
    match = _JSON_OBJECT.search(text)
    if match:
        try:
            data = json.loads(match.group(0))
        except json.JSONDecodeError:
            data = {}
        verdict = str(data.get("verdict", "")).strip().lower()
        if verdict in ("correct", "partiel", "incorrect"):
            return verdict, str(data.get("justification", ""))  # type: ignore[return-value]
    return "incorrect", f"sortie du juge illisible : {text[:120]}"


def judge(llm: LLMProvider, question: EvalQuestion, answer: str) -> tuple[Verdict, str]:
    user = (
        f"Question : {question.question}\n\nRéponse de référence : {question.reference_answer}"
        f"\n\nRéponse de l'assistant : {answer}"
    )
    return parse_verdict(llm.complete(JUDGE_SYSTEM, user).text)


def score(question: EvalQuestion, answer: Answer, judge_llm: LLMProvider | None) -> QuestionResult:
    expected_pages = {(s.source_id, s.page) for s in question.expected_sources}
    expected_docs = {s.source_id for s in question.expected_sources}
    retrieved = {(hit.chunk.source_id, hit.chunk.page) for hit in answer.retrieved}
    cited = {(c.source_id, c.page) for c in answer.citations}

    verdict: Verdict
    justification = ""
    if not question.answerable:
        verdict = "hors_corpus"
    elif answer.abstained:
        verdict = "abstention"
    elif judge_llm is None:
        verdict = "incorrect"
        justification = "aucun juge configuré"
    else:
        verdict, justification = judge(judge_llm, question, answer.text)

    return QuestionResult(
        id=question.id,
        answerable=question.answerable,
        answer=answer.text,
        abstained=answer.abstained,
        verdict=verdict,
        justification=justification,
        context_hit_page=bool(expected_pages & retrieved),
        context_hit_document=bool(expected_docs & {doc for doc, _ in retrieved}),
        citation_ok=bool(expected_pages & cited),
        latency_ms=answer.latency_ms,
        input_tokens=answer.input_tokens,
        output_tokens=answer.output_tokens,
    )


class Summary(BaseModel):
    exactitude: Rate  # verdict « correct » sur les questions avec réponse
    exactitude_correct_ou_partiel: Rate
    citations_correctes: Rate  # parmi les questions avec réponse auxquelles l'assistant a répondu
    contexte_page_attendue: Rate  # hit@k au niveau (document, page)
    contexte_document_attendu: Rate  # hit@k au niveau document
    refus_injustifies: Rate  # abstention sur une question qui a une réponse
    abstention_correcte: Rate  # abstention sur une question hors corpus
    reponses_incorrectes: int = 0  # verdict « incorrect » : réponse fausse affirmée
    latence_p50_ms: float
    latence_p95_ms: float
    tokens_entree_moyen: float
    tokens_sortie_moyen: float
    cout_1000_questions_usd: float


def summarize(
    results: list[QuestionResult], price_in_per_m: float, price_out_per_m: float
) -> Summary:
    answerable = [r for r in results if r.answerable]
    out_of_corpus = [r for r in results if not r.answerable]
    answered = [r for r in answerable if not r.abstained]
    n = len(results)
    mean_in = sum(r.input_tokens for r in results) / n if n else 0.0
    mean_out = sum(r.output_tokens for r in results) / n if n else 0.0
    latencies = [r.latency_ms for r in results]
    return Summary(
        exactitude=wilson(sum(r.verdict == "correct" for r in answerable), len(answerable)),
        exactitude_correct_ou_partiel=wilson(
            sum(r.verdict in ("correct", "partiel") for r in answerable), len(answerable)
        ),
        citations_correctes=wilson(sum(r.citation_ok for r in answered), len(answered)),
        contexte_page_attendue=wilson(sum(r.context_hit_page for r in answerable), len(answerable)),
        contexte_document_attendu=wilson(
            sum(r.context_hit_document for r in answerable), len(answerable)
        ),
        refus_injustifies=wilson(sum(r.abstained for r in answerable), len(answerable)),
        abstention_correcte=wilson(sum(r.abstained for r in out_of_corpus), len(out_of_corpus)),
        reponses_incorrectes=sum(r.verdict == "incorrect" for r in answerable),
        latence_p50_ms=percentile(latencies, 0.50),
        latence_p95_ms=percentile(latencies, 0.95),
        tokens_entree_moyen=mean_in,
        tokens_sortie_moyen=mean_out,
        cout_1000_questions_usd=1000
        * (mean_in * price_in_per_m + mean_out * price_out_per_m)
        / 1e6,
    )


def hit_at_k(question: EvalQuestion, hits: list[ScoredChunk], k: int, level: str = "page") -> bool:
    """La source attendue figure-t-elle parmi les k premiers passages ? (niveau page ou document)"""
    top = hits[:k]
    if level == "document":
        expected_docs = {s.source_id for s in question.expected_sources}
        return any(hit.chunk.source_id in expected_docs for hit in top)
    expected = {(s.source_id, s.page) for s in question.expected_sources}
    return any((hit.chunk.source_id, hit.chunk.page) in expected for hit in top)


def choose_threshold(answerable_scores: list[float]) -> float:
    """Règle fixée avant toute mesure : le plus haut seuil qui ne fait refuser aucune question
    de calibration ayant une réponse, c'est-à-dire le plus petit de leurs meilleurs scores.

    On privilégie l'absence de refus injustifiés ; le LLM reste le second garde-fou.
    """
    if not answerable_scores:
        raise ValueError("au moins une question avec réponse est nécessaire pour calibrer")
    return min(answerable_scores)


class Gate(BaseModel):
    """Seuils bloquants de l'évaluation en CI (eval/ci_gate.json), en nombres de questions."""

    correct_ou_partiel_min: int
    abstention_correcte_min: int
    reponses_incorrectes_max: int
    refus_injustifies_max: int


def check_gate(summary: Summary, gate: Gate) -> list[str]:
    """Renvoie la liste des seuils non respectés (vide = la CI passe)."""
    failures = []
    if summary.exactitude_correct_ou_partiel.count < gate.correct_ou_partiel_min:
        failures.append(
            f"correct ou partiel {summary.exactitude_correct_ou_partiel.count} "
            f"< {gate.correct_ou_partiel_min}"
        )
    if summary.abstention_correcte.count < gate.abstention_correcte_min:
        failures.append(
            f"abstention correcte {summary.abstention_correcte.count} "
            f"< {gate.abstention_correcte_min}"
        )
    if summary.reponses_incorrectes > gate.reponses_incorrectes_max:
        failures.append(
            f"réponses incorrectes {summary.reponses_incorrectes} > {gate.reponses_incorrectes_max}"
        )
    if summary.refus_injustifies.count > gate.refus_injustifies_max:
        failures.append(
            f"refus injustifiés {summary.refus_injustifies.count} > {gate.refus_injustifies_max}"
        )
    return failures
