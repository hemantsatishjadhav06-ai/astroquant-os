# Portable container for the AstroQuant OS Discovery Lab API.
# Works on Render (Docker runtime), Fly.io, Cloud Run, or locally.
FROM python:3.11-slim

# build-essential is needed to compile pyswisseph's C extension.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml ./
COPY python ./python
COPY README.md ./
RUN pip install --no-cache-dir -e .[api,data]

ENV PYTHONUNBUFFERED=1 \
    AQ_BROKER=nse
EXPOSE 8000

# Render/most PaaS inject $PORT; default to 8000 locally.
CMD ["sh", "-c", "uvicorn astroquant.api.app:app --host 0.0.0.0 --port ${PORT:-8000}"]
