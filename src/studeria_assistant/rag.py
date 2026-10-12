"""Réponse à une question : recherche des passages, génération avec citations, abstention."""

import re
import time
from typing import Protocol

from pydantic import BaseModel

from studeria_assistant.index import ScoredChunk
from studeria_assistant.llm import LLMProvider

ABSTENTION = "Je ne trouve pas cette information dans les documents."

SYSTEM_PROMPT = f"""Tu es un assistant qui répond aux questions sur des règlements et chartes \
d'établissements d'enseignement supérieur.
Règles :
- Réponds uniquement à partir des passages fournis, jamais de tes connaissances générales.
- Après chaque affirmation, cite le ou les passages utilisés sous la forme [1], [2]…
- Si les passages ne permettent pas de répondre, réponds exactement : « {ABSTENTION} »
- Réponds en français, en trois phrases au plus."""

_CITATION = re.compile(r"\[(\d+)\]")


class Retriever(Protocol):
    def search(self, query: str, k: int = 5) -> list[ScoredChunk]: ...


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


def build_user_prompt(question: str, passages: list[ScoredChunk]) -> str:
    blocks = [
        f"[{n}] {hit.chunk.title}, page {hit.chunk.page}\n{hit.chunk.text}"
        for n, hit in enumerate(passages, start=1)
    ]
    return "Passages :\n\n" + "\n\n".join(blocks) + f"\n\nQuestion : {question}"


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


def is_abstention(text: str) -> bool:
    return ABSTENTION.rstrip(".").lower() in text.lower()


class Assistant:
    def __init__(self, retriever: Retriever, llm: LLMProvider, k: int = 5) -> None:
        self.retriever = retriever
        self.llm = llm
        self.k = k

    def answer(self, question: str) -> Answer:
        start = time.perf_counter()
        passages = self.retriever.search(question, self.k)
        if not passages:  # rien à citer : on s'abstient sans appeler le LLM
            return Answer(
                question=question,
                text=ABSTENTION,
                abstained=True,
                citations=[],
                retrieved=[],
                latency_ms=(time.perf_counter() - start) * 1000,
            )
        response = self.llm.complete(SYSTEM_PROMPT, build_user_prompt(question, passages))
        abstained = is_abstention(response.text)
        return Answer(
            question=question,
            text=response.text,
            abstained=abstained,
            citations=[] if abstained else extract_citations(response.text, passages),
            retrieved=passages,
            latency_ms=(time.perf_counter() - start - response.rate_limit_wait_s) * 1000,
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
        )
