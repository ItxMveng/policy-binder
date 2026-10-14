# Image de l'API pour Hugging Face Spaces (SDK Docker, port 7860, utilisateur 1000).
# Les PDF officiels sont téléchargés pendant le build : aucun texte des règlements n'est versionné.
FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.12.23 /uv /usr/local/bin/uv
RUN useradd -m -u 1000 user
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy FASTEMBED_CACHE_PATH=/app/models PYTHONIOENCODING=utf-8
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project
COPY src ./src
COPY scripts ./scripts
COPY data/sources.yaml ./data/sources.yaml
RUN uv sync --frozen --no-dev
# Corpus et passages (BM25), puis préchargement des modèles locaux pour un démarrage rapide.
RUN uv run --no-dev python scripts/download_sources.py \
 && uv run --no-dev python scripts/ingest.py \
 && uv run --no-dev python -c "from policy_binder.embeddings import FastEmbedEmbedder; from policy_binder.rerank import FastEmbedReranker; FastEmbedEmbedder(); FastEmbedReranker()"
RUN chown -R user:user /app
USER user
ENV PATH="/app/.venv/bin:$PATH" PORT=7860
EXPOSE 7860
CMD ["sh", "-c", "uvicorn policy_binder.api:app --host 0.0.0.0 --port ${PORT}"]
