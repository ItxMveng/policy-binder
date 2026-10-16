import pytest
from fastapi.testclient import TestClient

from policy_binder.api import app, get_assistant
from policy_binder.rag import Assistant
from tests.test_rag import PASSAGES, FakeLLM, FakeRetriever

client = TestClient(app)


def test_health_returns_ok() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_ask_returns_answer_with_citations() -> None:
    assistant = Assistant(FakeRetriever(PASSAGES), FakeLLM("Il faut le déclarer [1]."))
    app.dependency_overrides[get_assistant] = lambda: assistant
    try:
        response = client.post("/ask", json={"question": "Puis-je utiliser une IA ?"})
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200
    body = response.json()
    assert body["citations"][0]["title"] == "Charte IA"
    assert body["abstained"] is False


def test_ask_rejects_empty_question() -> None:
    assistant = Assistant(FakeRetriever(PASSAGES), FakeLLM("non appelé"))
    app.dependency_overrides[get_assistant] = lambda: assistant
    try:
        assert client.post("/ask", json={"question": ""}).status_code == 422
    finally:
        app.dependency_overrides.clear()


def test_ask_without_key_returns_503(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.chdir("/")  # aucun fichier .env lu
    assert client.post("/ask", json={"question": "Bonjour ?"}).status_code == 503


def test_sources_lists_official_urls() -> None:
    response = client.get("/sources")
    assert response.status_code == 200
    sources = response.json()
    assert len(sources) >= 6
    assert all(source["url"].startswith("https://") for source in sources)


def test_cors_allows_local_front() -> None:
    response = client.options(
        "/ask",
        headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "POST"},
    )
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"


def test_ask_returns_429_when_limit_reached(monkeypatch: pytest.MonkeyPatch) -> None:
    from policy_binder import api
    from policy_binder.ratelimit import DemoLimiter

    monkeypatch.setattr(api, "limiter", DemoLimiter(per_ip=1, window_s=600, daily=100))
    assistant = Assistant(FakeRetriever(PASSAGES), FakeLLM("Il faut le déclarer [1]."))
    app.dependency_overrides[get_assistant] = lambda: assistant
    try:
        assert client.post("/ask", json={"question": "Première ?"}).status_code == 200
        second = client.post("/ask", json={"question": "Deuxième ?"})
    finally:
        app.dependency_overrides.clear()
    assert second.status_code == 429
    assert "réessayez" in second.json()["detail"]


def test_cors_origins_are_comma_separated(monkeypatch: pytest.MonkeyPatch) -> None:
    from policy_binder.config import Settings

    monkeypatch.setenv("ALLOWED_ORIGINS", " https://a.vercel.app , http://localhost:5173,")
    assert Settings().cors_origins == ["https://a.vercel.app", "http://localhost:5173"]
