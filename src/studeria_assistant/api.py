"""API HTTP de l'assistant."""

from fastapi import FastAPI

from studeria_assistant import __version__

app = FastAPI(title="Studeria Assistant", version=__version__)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "version": __version__}
