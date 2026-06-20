# AI Resume Tailor — container image for Render / any Docker host.
FROM python:3.12-slim

# System deps + the tectonic LaTeX engine (self-contained binary).
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates fontconfig \
    && rm -rf /var/lib/apt/lists/*
RUN curl --proto '=https' --tlsv1.2 -fsSL https://drop-sh.fullyjustified.net | sh \
    && mv tectonic /usr/local/bin/tectonic
ENV RESUME_TAILOR_TECTONIC=/usr/local/bin/tectonic

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./backend/
WORKDIR /app/backend

# Pre-warm tectonic's package bundle so the first PDF compile isn't slow / network-bound.
RUN printf '\\documentclass{article}\\begin{document}warmup\\end{document}' > /tmp/w.tex \
    && tectonic --outdir /tmp /tmp/w.tex || true

ENV PYTHONUNBUFFERED=1
EXPOSE 8000
# Render injects $PORT; default to 8000 for local `docker run`.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
