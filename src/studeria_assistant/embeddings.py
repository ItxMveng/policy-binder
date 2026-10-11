"""Embeddings : une interface, une implémentation locale (fastembed, sans clé ni coût par appel)."""

from collections.abc import Sequence
from typing import Protocol

DEFAULT_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


class Embedder(Protocol):
    @property
    def dim(self) -> int: ...

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]: ...

    def embed_query(self, text: str) -> list[float]: ...


class FastEmbedEmbedder:
    """Modèle multilingue (FR/EN) exécuté en local sur CPU (ONNX), téléchargé au premier appel."""

    def __init__(self, model_name: str = DEFAULT_MODEL) -> None:
        from fastembed import TextEmbedding  # import tardif : les tests n'en ont pas besoin

        self._model = TextEmbedding(model_name=model_name)
        self._dim = len(self.embed_query("dimension"))

    @property
    def dim(self) -> int:
        return self._dim

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        return [vector.tolist() for vector in self._model.embed(list(texts))]

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]
