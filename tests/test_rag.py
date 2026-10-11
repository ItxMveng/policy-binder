import json

import httpx

from studeria_assistant.index import ScoredChunk
from studeria_assistant.ingest import Chunk
from studeria_assistant.llm import LLMResponse, MistralProvider
from studeria_assistant.rag import ABSTENTION, Assistant, build_user_prompt, extract_citations

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


def test_mistral_provider_parses_response_and_usage() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert body["temperature"] == 0
        assert request.headers["Authorization"] == "Bearer test-key"
        return httpx.Response(
            200,
            json={
                "model": "mistral-small-latest",
                "choices": [{"message": {"content": "Réponse [1]."}}],
                "usage": {"prompt_tokens": 321, "completion_tokens": 12},
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    response = MistralProvider("test-key", client=client).complete("système", "question")
    assert response.text == "Réponse [1]."
    assert (response.input_tokens, response.output_tokens) == (321, 12)
