"""Interface LLMProvider : changer de fournisseur = écrire une classe (ou une URL) dans ce fichier.

Mistral, Groq, Ollama et Gemini exposent tous le même format d'API « chat completions » (celui
d'OpenAI) : une seule classe les couvre, seuls l'URL, la clé et le nom du modèle changent.
"""

import time
from typing import Protocol

import httpx
from pydantic import BaseModel

BASE_URLS = {
    "mistral": "https://api.mistral.ai/v1",
    "groq": "https://api.groq.com/openai/v1",
    "ollama": "http://localhost:11434/v1",  # local, sans clé
}
MAX_RETRIES = 5


class LLMResponse(BaseModel):
    text: str
    model: str
    input_tokens: int
    output_tokens: int


class LLMProvider(Protocol):
    def complete(self, system: str, user: str) -> LLMResponse: ...


class ChatCompletionsProvider:
    """Appel à une API au format chat completions, température 0 pour des réponses stables.

    Les offres gratuites limitent le débit (erreur 429) : on attend le délai indiqué par
    l'en-tête Retry-After (ou un délai croissant) avant de réessayer.
    """

    def __init__(
        self,
        base_url: str,
        model: str,
        api_key: str | None = None,
        client: httpx.Client | None = None,
        sleep: float = 2.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self._headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        self._client = client or httpx.Client(timeout=120.0)
        self._sleep = sleep

    def complete(self, system: str, user: str) -> LLMResponse:
        payload = {
            "model": self.model,
            "temperature": 0,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        for attempt in range(MAX_RETRIES + 1):
            response = self._client.post(
                f"{self.base_url}/chat/completions", headers=self._headers, json=payload
            )
            if response.status_code != 429 or attempt == MAX_RETRIES:
                break
            retry_after = response.headers.get("retry-after")
            delay = float(retry_after) if retry_after else self._sleep * 2**attempt
            time.sleep(delay)
        response.raise_for_status()
        body = response.json()
        usage = body.get("usage") or {}
        return LLMResponse(
            text=body["choices"][0]["message"]["content"],
            model=body.get("model", self.model),
            input_tokens=usage.get("prompt_tokens", 0),
            output_tokens=usage.get("completion_tokens", 0),
        )


def make_provider(
    name: str, model: str, api_key: str | None = None, client: httpx.Client | None = None
) -> ChatCompletionsProvider:
    if name not in BASE_URLS:
        raise ValueError(f"fournisseur inconnu : {name} (attendu : {', '.join(BASE_URLS)})")
    return ChatCompletionsProvider(BASE_URLS[name], model, api_key, client)
