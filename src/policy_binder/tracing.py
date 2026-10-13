"""Trace de chaque question (recherche, génération, abstention) : Langfuse si configuré.

L'assistant ne dépend que de l'interface `Tracer` : en test et sans clés, `NoopTracer` ne fait
rien ; en production, `LangfuseTracer` envoie les traces à Langfuse Cloud (latence, tokens).
"""

from collections.abc import Iterator
from contextlib import AbstractContextManager, contextmanager
from typing import Any, Protocol


class Observation(Protocol):
    def update(self, **fields: Any) -> Any: ...


class Tracer(Protocol):
    def observe(
        self, name: str, as_type: str = "span", **fields: Any
    ) -> AbstractContextManager[Observation]: ...


class _NoopObservation:
    def update(self, **fields: Any) -> None:
        return None


class NoopTracer:
    @contextmanager
    def observe(self, name: str, as_type: str = "span", **fields: Any) -> Iterator[Observation]:
        yield _NoopObservation()


class LangfuseTracer:
    """Adaptateur vers le SDK Langfuse (v4, basé sur OpenTelemetry)."""

    def __init__(self, public_key: str, secret_key: str, host: str) -> None:
        from langfuse import Langfuse

        # Typé Any : le SDK expose une surcharge par type d'observation, alors que ce code reçoit
        # le type en paramètre ; on garde une seule méthode générique.
        self._client: Any = Langfuse(public_key=public_key, secret_key=secret_key, host=host)

    def observe(
        self, name: str, as_type: str = "span", **fields: Any
    ) -> AbstractContextManager[Observation]:
        manager: AbstractContextManager[Observation] = self._client.start_as_current_observation(
            name=name,
            as_type=as_type,
            **fields,
        )
        return manager

    def flush(self) -> None:
        self._client.flush()
