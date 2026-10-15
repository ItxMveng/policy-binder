# Image de production de l'API (Azure Container Apps ; compatible Cloud Run).
# Publique : elle ne contient aucun texte des règlements. Les PDF officiels sont téléchargés et
# découpés au démarrage du conteneur (deploy/start.sh) ; les modèles locaux sont préchargés au build.
FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.12.23 /uv /usr/local/bin/uv
RUN useradd -m -u 1000 app
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy FASTEMBED_CACHE_PATH=/app/models PYTHONIOENCODING=utf-8
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project
COPY src ./src
COPY scripts/download_sources.py scripts/ingest.py ./scripts/
COPY data/sources.yaml ./data/sources.yaml
COPY deploy/start.sh ./deploy/start.sh
RUN uv sync --frozen --no-dev \
 && uv run --no-dev python -c "from policy_binder.embeddings import FastEmbedEmbedder; from policy_binder.rerank import FastEmbedReranker; FastEmbedEmbedder(); FastEmbedReranker()" \
 && chown -R app:app /app
USER app
ENV PATH="/app/.venv/bin:$PATH" PORT=8080
EXPOSE 8080
CMD ["sh", "deploy/start.sh"]
