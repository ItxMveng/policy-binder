"""Interface LLMProvider : changer de fournisseur = écrire une classe dans ce fichier."""

from typing import Protocol

import httpx
from pydantic import BaseModel

MISTRAL_ENDPOINT = "https://api.mistral.ai/v1/chat/completions"


class LLMResponse(BaseModel):
    text: str
    model: str
    input_tokens: int
    output_tokens: int


class LLMProvider(Protocol):
    def complete(self, system: str, user: str) -> LLMResponse: ...


class MistralProvider:
    """Appel direct à l'API Mistral (chat completions), température 0 pour des réponses stables."""

    def __init__(
        self,
        api_key: str,
        model: str = "mistral-small-latest",
        client: httpx.Client | None = None,
    ) -> None:
        self.model = model
        self._api_key = api_key
        self._client = client or httpx.Client(timeout=60.0)

    def complete(self, system: str, user: str) -> LLMResponse:
        response = self._client.post(
            MISTRAL_ENDPOINT,
            headers={"Authorization": f"Bearer {self._api_key}"},
            json={
                "model": self.model,
                "temperature": 0,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            },
        )
        response.raise_for_status()
        body = response.json()
        usage = body.get("usage", {})
        return LLMResponse(
            text=body["choices"][0]["message"]["content"],
            model=body.get("model", self.model),
            input_tokens=usage.get("prompt_tokens", 0),
            output_tokens=usage.get("completion_tokens", 0),
        )
