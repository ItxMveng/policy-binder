import json

import httpx
import pytest

from policy_binder.index import ScoredChunk
from policy_binder.ingest import Chunk
from policy_binder.llm import ChatCompletionsProvider, LLMResponse, make_provider
from policy_binder.rag import (
    ABSTENTION,
    ABSTENTION_PARTIELLE,
    Assistant,
    build_user_prompt,
    extract_citations,
    is_abstention,
    is_partial,
)

PASSAGES = [
    ScoredChunk(
        chunk=Chunk(
            id="ia-p11-c0",
            source_id="ia",
            title="Charte IA",
            page=11,
            text="L'usage d'une IA générative doit être déclaré.",
        ),
        score=0.8,
    ),
    ScoredChunk(
        chunk=Chunk(
            id="examens-p3-c0",
            source_id="examens",
            title="Charte des examens",
            page=3,
            text="Toute fraude entraîne une procédure disciplinaire.",
        ),
        score=0.5,
    ),
]


class FakeRetriever:
    def __init__(self, passages: list[ScoredChunk]) -> None:
        self.passages = passages

    def search(self, query: str, k: int = 5) -> list[ScoredChunk]:
        return self.passages[:k]


class FakeLLM:
    def __init__(self, text: str) -> None:
        self.text = text
        self.calls = 0

    def complete(self, system: str, user: str) -> LLMResponse:
        self.calls += 1
        return LLMResponse(text=self.text, model="fake", input_tokens=100, output_tokens=20)


def test_answer_keeps_valid_citations_only() -> None:
    llm = FakeLLM("Il faut déclarer l'usage [1]. Voir aussi [1] et [7].")
    answer = Assistant(FakeRetriever(PASSAGES), llm).answer("Puis-je utiliser une IA ?")
    assert not answer.abstained
    assert [c.chunk_id for c in answer.citations] == ["ia-p11-c0"]
    assert answer.citations[0].page == 11
    assert answer.input_tokens == 100


def test_abstention_from_llm_has_no_citations() -> None:
    llm = FakeLLM(f"{ABSTENTION} [2]")
    answer = Assistant(FakeRetriever(PASSAGES), llm).answer("Menu du restaurant ?")
    assert answer.abstained
    assert answer.citations == []


def test_no_passage_means_abstention_without_llm_call() -> None:
    llm = FakeLLM("ne doit pas être appelé")
    answer = Assistant(FakeRetriever([]), llm).answer("Question ?")
    assert answer.abstained
    assert llm.calls == 0


def test_prompt_numbers_passages_with_title_and_page() -> None:
    prompt = build_user_prompt("Q ?", PASSAGES)
    assert "[1] Charte IA, page 11" in prompt
    assert "[2] Charte des examens, page 3" in prompt


def test_citations_are_deduplicated_in_order() -> None:
    citations = extract_citations("A [2]. B [1]. C [2].", PASSAGES)
    assert [c.number for c in citations] == [2, 1]


def _chat_response(text: str) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "model": "llama-3.3-70b-versatile",
            "choices": [{"message": {"content": text}}],
            "usage": {"prompt_tokens": 321, "completion_tokens": 12},
        },
    )


def test_provider_parses_response_and_usage() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert request.url == "https://api.groq.com/openai/v1/chat/completions"
        assert body["temperature"] == 0
        assert request.headers["Authorization"] == "Bearer test-key"
        return _chat_response("Réponse [1].")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    provider = make_provider("groq", "llama-3.3-70b-versatile", "test-key", client)
    response = provider.complete("système", "question")
    assert response.text == "Réponse [1]."
    assert (response.input_tokens, response.output_tokens) == (321, 12)


def test_provider_retries_after_rate_limit() -> None:
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        if len(calls) == 1:
            return httpx.Response(429, headers={"retry-after": "0"})
        return _chat_response("ok")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    provider = ChatCompletionsProvider("https://example.org/v1", "m", client=client)
    assert provider.complete("s", "u").text == "ok"
    assert len(calls) == 2


def test_ollama_needs_no_key_and_unknown_provider_fails() -> None:
    assert make_provider("ollama", "llama3.1:8b").base_url == "http://localhost:11434/v1"
    with pytest.raises(ValueError):
        make_provider("inconnu", "m")


def test_provider_retries_after_network_error() -> None:
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        if len(calls) == 1:
            raise httpx.ConnectError("connexion réinitialisée")
        return _chat_response("ok")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    provider = ChatCompletionsProvider("https://example.org/v1", "m", client=client, sleep=0)
    response = provider.complete("s", "u")
    assert response.text == "ok"
    assert response.rate_limit_wait_s >= 0


def test_low_top_score_abstains_before_llm() -> None:
    llm = FakeLLM("ne doit pas être appelé")
    answer = Assistant(FakeRetriever(PASSAGES), llm, min_score=0.9).answer("Hors sujet ?")
    assert answer.abstained and answer.abstained_before_llm
    assert llm.calls == 0


def test_top_score_above_threshold_calls_llm() -> None:
    llm = FakeLLM("Il faut déclarer l'usage [1].")
    answer = Assistant(FakeRetriever(PASSAGES), llm, min_score=0.5).answer("IA ?")
    assert not answer.abstained and llm.calls == 1


class RecordingTracer:
    """Faux traceur : enregistre les étapes ouvertes et les champs mis à jour."""

    def __init__(self) -> None:
        self.steps: list[tuple[str, str]] = []
        self.updates: dict[str, dict[str, object]] = {}

    def observe(self, name: str, as_type: str = "span", **fields: object):  # type: ignore[no-untyped-def]
        from contextlib import contextmanager

        tracer = self

        class Step:
            def update(self, **values: object) -> None:
                tracer.updates.setdefault(name, {}).update(values)

        @contextmanager
        def manager():  # type: ignore[no-untyped-def]
            tracer.steps.append((name, as_type))
            yield Step()

        return manager()


def test_trace_records_retrieval_generation_and_outcome() -> None:
    tracer = RecordingTracer()
    llm = FakeLLM("Il faut déclarer l'usage [1].")
    Assistant(FakeRetriever(PASSAGES), llm, tracer=tracer).answer("IA ?")
    assert tracer.steps == [
        ("question", "chain"),
        ("recherche", "retriever"),
        ("generation", "generation"),
    ]
    assert tracer.updates["generation"]["usage_details"] == {"input": 100, "output": 20}
    metadata = tracer.updates["question"]["metadata"]
    assert isinstance(metadata, dict) and metadata["abstention"] is False


def test_trace_without_generation_when_abstaining_before_llm() -> None:
    tracer = RecordingTracer()
    Assistant(FakeRetriever(PASSAGES), FakeLLM("non"), min_score=0.9, tracer=tracer).answer("?")
    assert [name for name, _ in tracer.steps] == ["question", "recherche"]


def _passage(source_id: str, page: int, score: float) -> ScoredChunk:
    chunk = Chunk(
        id=f"{source_id}-p{page}-c0", source_id=source_id, title=source_id, page=page, text="…"
    )
    return ScoredChunk(chunk=chunk, score=score)


class QueryRecordingRetriever(FakeRetriever):
    def __init__(self, passages: list[ScoredChunk]) -> None:
        super().__init__(passages)
        self.queries: list[tuple[str, int]] = []

    def search(self, query: str, k: int = 5) -> list[ScoredChunk]:
        self.queries.append((query, k))
        return super().search(query, k)


class PromptRecordingLLM(FakeLLM):
    def complete(self, system: str, user: str) -> LLMResponse:
        self.user = user
        return super().complete(system, user)


def test_partial_answer_keeps_citations_and_is_not_an_abstention() -> None:
    text = (
        "À l'UBO, l'année est validée avec une moyenne d'au moins 10/20 [1]. "
        f"{ABSTENTION_PARTIELLE} l'ENIB."
    )
    answer = Assistant(FakeRetriever(PASSAGES), FakeLLM(text)).answer(
        "Moyenne pour réussir l'année ?"
    )
    assert not answer.abstained and answer.partial
    assert [c.number for c in answer.citations] == [1]


def test_only_abstention_sentences_is_a_full_abstention() -> None:
    assert is_abstention(f"« {ABSTENTION} »")
    assert is_abstention(f"{ABSTENTION_PARTIELLE} l'UBO. {ABSTENTION_PARTIELLE} l'ENIB.")
    assert not is_partial(ABSTENTION)
    assert not is_abstention("Il faut 10/20 [1].")


def test_question_on_two_institutions_is_searched_per_institution() -> None:
    hits = [
        _passage("ubo-regime-etudes", 7, -1.8),
        _passage("imt-reglement", 2, -1.0),
        _passage("ubo-regime-etudes", 13, -2.7),
        _passage("enib-droits", 1, -4.4),
    ]
    retriever = QueryRecordingRetriever(hits)
    llm = PromptRecordingLLM(f"Il faut 10/20 [1]. {ABSTENTION_PARTIELLE} l'ENIB.")
    question = "Quelle moyenne pour réussir mon année à l'UBO, à l'ENIB et à IMT Atlantique ?"
    hits.pop(1)  # aucun candidat pour IMT Atlantique
    answer = Assistant(retriever, llm, min_score=-2.36).answer(question)
    # Recherche du sujet seul, une fois, sur assez de candidats pour couvrir chaque établissement.
    assert retriever.queries == [("Quelle moyenne pour réussir mon année ?", 20)]
    # Seuil sur le meilleur passage seulement : le passage ENIB, plus faible, est transmis au LLM.
    sources = [h.chunk.source_id for h in answer.retrieved]
    assert sources == ["ubo-regime-etudes", "ubo-regime-etudes", "enib-droits"]
    assert "Aucun passage pertinent n'a été trouvé pour : IMT Atlantique." in llm.user
    assert answer.partial and not answer.abstained


def test_two_institutions_without_any_answer_abstain_before_llm() -> None:
    retriever = FakeRetriever([_passage("ubo-x", 1, -5.0), _passage("enib-y", 1, -6.0)])
    llm = FakeLLM("ne doit pas être appelé")
    answer = Assistant(retriever, llm, min_score=-2.36).answer("Repas à l'UBO et à l'ENIB ?")
    assert answer.abstained and answer.abstained_before_llm and llm.calls == 0


def test_tool_style_citations_are_normalized() -> None:
    llm = FakeLLM("Le téléphone doit être déposé à l'entrée【1†L3-L5】【2†L…】.")
    answer = Assistant(FakeRetriever(PASSAGES), llm).answer("Téléphone ?")
    assert answer.text == "Le téléphone doit être déposé à l'entrée[1][2]."
    assert [c.number for c in answer.citations] == [1, 2]
