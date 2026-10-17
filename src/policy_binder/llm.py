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
RETRY_STATUSES = {429, 500, 502, 503}  # débit dépassé ou incident passager du fournisseur


class LLMUnavailableError(RuntimeError):
    """Le fournisseur demande d'attendre plus que l'appelant ne l'accepte (quota atteint)."""

    def __init__(self, retry_after_s: float) -> None:
        super().__init__(f"fournisseur indisponible, réessayer dans {retry_after_s:.0f} s")
        self.retry_after_s = retry_after_s


class LLMResponse(BaseModel):
    text: str
    model: str
    input_tokens: int
    output_tokens: int
    # Temps passé à attendre après un refus de débit (429) : exclu des mesures de latence.
    rate_limit_wait_s: float = 0.0


class LLMProvider(Protocol):
    def complete(self, system: str, user: str) -> LLMResponse: ...


class ChatCompletionsProvider:
    """Appel à une API au format chat completions, température 0 pour des réponses stables.

    Les offres gratuites limitent le débit (erreur 429) : on attend le délai indiqué par
    l'en-tête Retry-After (ou un délai croissant) avant de réessayer.
    `max_wait_s` borne l'attente cumulée : une démo en ligne préfère répondre « réessayez plus
    tard » tout de suite plutôt que d'attendre la fin d'un quota quotidien. Sans borne (None),
    on attend : c'est le comportement voulu pour les évaluations.
    """

    def __init__(
        self,
        base_url: str,
        model: str,
        api_key: str | None = None,
        client: httpx.Client | None = None,
        sleep: float = 2.0,
        max_wait_s: float | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self._headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        self._client = client or httpx.Client(timeout=120.0)
        self._sleep = sleep
        self._max_wait_s = max_wait_s

    def complete(self, system: str, user: str) -> LLMResponse:
        payload = {
            "model": self.model,
            "temperature": 0,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        # waited = durée des tentatives ratées + attentes : exclue de la latence mesurée.
        waited = 0.0
        for attempt in range(MAX_RETRIES + 1):
            started = time.perf_counter()
            last_attempt = attempt == MAX_RETRIES
            try:
                response = self._client.post(
                    f"{self.base_url}/chat/completions", headers=self._headers, json=payload
                )
            except httpx.TransportError:  # coupure réseau passagère : on réessaie
                if last_attempt:
                    raise
                delay = self._sleep * 2**attempt
            else:
                if response.status_code not in RETRY_STATUSES or last_attempt:
                    break
                retry_after = response.headers.get("retry-after")
                delay = float(retry_after) if retry_after else self._sleep * 2**attempt
                if self._max_wait_s is not None and waited + delay > self._max_wait_s:
                    raise LLMUnavailableError(delay)
            time.sleep(delay)
            waited += time.perf_counter() - started
        response.raise_for_status()
        body = response.json()
        usage = body.get("usage") or {}
        return LLMResponse(
            text=body["choices"][0]["message"]["content"],
            model=body.get("model", self.model),
            input_tokens=usage.get("prompt_tokens", 0),
            output_tokens=usage.get("completion_tokens", 0),
            rate_limit_wait_s=waited,
        )


def make_provider(
    name: str,
    model: str,
    api_key: str | None = None,
    client: httpx.Client | None = None,
    max_wait_s: float | None = None,
) -> ChatCompletionsProvider:
    if name not in BASE_URLS:
        raise ValueError(f"fournisseur inconnu : {name} (attendu : {', '.join(BASE_URLS)})")
    return ChatCompletionsProvider(BASE_URLS[name], model, api_key, client, max_wait_s=max_wait_s)
