# Soikio thesis red-team — deployable image (STORY-06.3.01, ADR-0010).
# Pinned base + pinned deps (requirements.txt) for a reproducible build.
FROM python:3.11-slim

# No secret in any layer: the Anthropic key is fetched from Key Vault at runtime
# via the managed identity (src/config.py). Only non-secret config is set here.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/src \
    PORT=8000

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App code + prompt templates (prompts/ resolves to _P=/app, sibling of src/).
COPY src/ ./src/
COPY prompts/ ./prompts/

EXPOSE 8000

# Container Apps health probe hits /health; uvicorn serves server:app from src/.
CMD ["sh", "-c", "uvicorn server:app --app-dir src --host 0.0.0.0 --port ${PORT}"]
