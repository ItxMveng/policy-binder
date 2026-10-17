"""Réponse à une question : recherche des passages, génération avec citations, abstention."""

import re
import time
from collections.abc import Callable, Sequence
from typing import Protocol, runtime_checkable

from pydantic import BaseModel

from policy_binder.etablissements import Etablissement, etablissements_cites, sans_etablissements
from policy_binder.index import ScoredChunk
from policy_binder.llm import LLMProvider
from policy_binder.tracing import NoopTracer, Tracer

ABSTENTION = "Je ne trouve pas cette information dans les documents."
ABSTENTION_PARTIELLE = "Je ne trouve pas cette information dans les documents pour"
_PHRASE_ABSTENTION = ABSTENTION.rstrip(".").lower()

SYSTEM_PROMPT = f"""Tu es un assistant qui répond aux questions sur des règlements et chartes \
d'établissements d'enseignement supérieur.
Règles :
- Réponds uniquement à partir des passages fournis, jamais de tes connaissances générales.
- Après chaque affirmation, cite le ou les passages utilisés sous la forme [1], [2]…
- Si les passages ne permettent de répondre à aucune partie de la question, réponds exactement : \
« {ABSTENTION} »
- Si la question a plusieurs parties (par exemple plusieurs établissements) et que les passages \
ne répondent qu'à certaines, réponds d'abord à celles-ci avec leurs citations, puis écris pour \
chaque partie manquante : « {ABSTENTION_PARTIELLE} <partie>. »
- Réponds en français, en trois phrases au plus par partie de la question."""

# Candidats relus par le reranker pour une question qui cite plusieurs établissements.
CANDIDATS_PAR_SUJET = 20

_CITATION = re.compile(r"\[(\d+)\]")
# gpt-oss cite parfois au format de ses outils de navigation : 【1†L3-L5】 au lieu de [1].
_CITATION_OUTIL = re.compile(r"【(\d+)†[^】]*】")


class Retriever(Protocol):
    def search(self, query: str, k: int = 5) -> list[ScoredChunk]: ...


@runtime_checkable
class GroupedRetriever(Protocol):
    """Recherche qui réserve des candidats à chaque groupe de sources (voir rerank.py)."""

    def search(self, query: str, k: int = 5) -> list[ScoredChunk]: ...

    def search_grouped(
        self, query: str, groups: Sequence[tuple[str, Callable[[str], bool]]]
    ) -> list[list[ScoredChunk]]: ...


class Citation(BaseModel):
    number: int
    chunk_id: str
    source_id: str
    title: str
    page: int


class Answer(BaseModel):
    question: str
    text: str
    abstained: bool
    citations: list[Citation]
    retrieved: list[ScoredChunk]
    latency_ms: float
    input_tokens: int = 0
    output_tokens: int = 0
    # Abstention décidée avant le LLM (aucun passage, ou meilleur score sous le seuil).
    abstained_before_llm: bool = False
    # Réponse à une partie de la question seulement ; l'autre est signalée comme introuvable.
    partial: bool = False


def build_user_prompt(
    question: str, passages: list[ScoredChunk], introuvables: list[str] | None = None
) -> str:
    blocks = [
        f"[{n}] {hit.chunk.title}, page {hit.chunk.page}\n{hit.chunk.text}"
        for n, hit in enumerate(passages, start=1)
    ]
    note = ""
    if introuvables:
        note = "\n\nAucun passage pertinent n'a été trouvé pour : " + ", ".join(introuvables) + "."
    return "Passages :\n\n" + "\n\n".join(blocks) + note + f"\n\nQuestion : {question}"


def normalize_citations(text: str) -> str:
    return _CITATION_OUTIL.sub(r"[\1]", text)


def extract_citations(text: str, passages: list[ScoredChunk]) -> list[Citation]:
    """Garde les numéros cités qui existent vraiment, une fois chacun, dans l'ordre d'apparition."""
    seen: list[int] = []
    for match in _CITATION.finditer(text):
        number = int(match.group(1))
        if 1 <= number <= len(passages) and number not in seen:
            seen.append(number)
    return [
        Citation(
            number=n,
            chunk_id=passages[n - 1].chunk.id,
            source_id=passages[n - 1].chunk.source_id,
            title=passages[n - 1].chunk.title,
            page=passages[n - 1].chunk.page,
        )
        for n in seen
    ]


def _phrases_hors_abstention(text: str) -> list[str]:
    phrases = re.split(r"(?<=[.!?»])\s+", _CITATION.sub("", text))
    return [p for p in phrases if _PHRASE_ABSTENTION not in p.lower() and re.search(r"\w", p)]


def is_abstention(text: str) -> bool:
    """Abstention totale : la réponse ne contient rien d'autre que la phrase d'abstention."""
    return not _phrases_hors_abstention(text)


def is_partial(text: str) -> bool:
    """Réponse partielle : une partie est répondue, une autre signalée comme introuvable."""
    return _PHRASE_ABSTENTION in text.lower() and not is_abstention(text)


class Assistant:
    """`min_score` : seuil d'abstention sur le score du meilleur passage (score du reranker).

    Sous le seuil, aucun passage n'est jugé assez pertinent : on s'abstient sans appeler le LLM.
    C'est un garde-fou indépendant du modèle, et une économie sur les questions hors sujet.
    """

    def __init__(
        self,
        retriever: Retriever,
        llm: LLMProvider,
        k: int = 5,
        min_score: float | None = None,
        tracer: Tracer | None = None,
    ) -> None:
        self.retriever = retriever
        self.llm = llm
        self.k = k
        self.min_score = min_score
        self.tracer: Tracer = tracer or NoopTracer()

    def answer(self, question: str) -> Answer:
        with self.tracer.observe("question", as_type="chain", input=question) as trace:
            answer = self._answer(question)
            trace.update(
                output=answer.text,
                metadata={
                    "abstention": answer.abstained,
                    "abstention_avant_llm": answer.abstained_before_llm,
                    "citations": [f"{c.source_id} p.{c.page}" for c in answer.citations],
                    "latence_ms": round(answer.latency_ms),
                },
            )
        return answer

    def _answer(self, question: str) -> Answer:
        start = time.perf_counter()
        etablissements = etablissements_cites(question)
        introuvables: list[str] = []
        with self.tracer.observe("recherche", as_type="retriever", input=question) as step:
            if len(etablissements) >= 2:
                passages, introuvables = self._search_par_etablissement(question, etablissements)
            else:
                passages = self.retriever.search(question, self.k)
            step.update(
                output=[
                    {"passage": hit.chunk.id, "score": round(hit.score, 3)} for hit in passages
                ],
                metadata={"introuvables": introuvables},
            )
        if not passages or self._sous_le_seuil(passages[0]):
            return Answer(
                question=question,
                text=ABSTENTION,
                abstained=True,
                citations=[],
                retrieved=passages,
                latency_ms=(time.perf_counter() - start) * 1000,
                abstained_before_llm=True,
            )
        prompt = build_user_prompt(question, passages, introuvables)
        with self.tracer.observe("generation", as_type="generation", input=prompt) as step:
            response = self.llm.complete(SYSTEM_PROMPT, prompt)
            step.update(
                output=response.text,
                model=response.model,
                usage_details={"input": response.input_tokens, "output": response.output_tokens},
            )
        text = normalize_citations(response.text)
        abstained = is_abstention(text)
        return Answer(
            question=question,
            text=text,
            abstained=abstained,
            partial=is_partial(text),
            citations=[] if abstained else extract_citations(text, passages),
            retrieved=passages,
            latency_ms=(time.perf_counter() - start - response.rate_limit_wait_s) * 1000,
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
        )

    def _sous_le_seuil(self, hit: ScoredChunk) -> bool:
        return self.min_score is not None and hit.score < self.min_score

    def _search_par_etablissement(
        self, question: str, etablissements: list[Etablissement]
    ) -> tuple[list[ScoredChunk], list[str]]:
        """Réunit les meilleurs passages de chaque établissement cité.

        Le reranker note le sujet seul : la mention de plusieurs établissements dilue son score au
        point de faire passer la bonne page sous le seuil. La première étape cherche, elle, la
        question restreinte à chaque établissement, pour que ses pages figurent parmi les candidats.
        Le seuil reste appliqué au meilleur passage, comme pour une question simple (c'est ainsi
        qu'il a été calibré) ; le LLM dit ensuite, partie par partie, ce qu'il trouve ou non.
        Renvoie les passages triés par score et les établissements sans aucun candidat.
        """
        sujet = sans_etablissements(question)
        if isinstance(self.retriever, GroupedRetriever):
            groupes = self.retriever.search_grouped(
                sujet, [(sans_etablissements(question, e), e.possede) for e in etablissements]
            )
        else:
            hits = self.retriever.search(sujet, CANDIDATS_PAR_SUJET)
            groupes = [[h for h in hits if e.possede(h.chunk.source_id)] for e in etablissements]
        par_etablissement = max(2, -(-self.k // len(etablissements)))
        passages = [hit for siens in groupes for hit in siens[:par_etablissement]]
        introuvables = [
            e.nom for e, siens in zip(etablissements, groupes, strict=True) if not siens
        ]
        passages.sort(key=lambda hit: hit.score, reverse=True)
        return passages, introuvables
