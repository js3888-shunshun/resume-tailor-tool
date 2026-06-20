# AI Resume Tailor — container image for Render / any Docker host.
FROM python:3.12-slim

# System deps + the tectonic LaTeX engine (self-contained binary).
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates fontconfig \
    && rm -rf /var/lib/apt/lists/*
RUN curl --proto '=https' --tlsv1.2 -fsSL https://drop-sh.fullyjustified.net | sh \
    && mv tectonic /usr/local/bin/tectonic
ENV RESUME_TAILOR_TECTONIC=/usr/local/bin/tectonic
# Pin the cache dir so the build-time prewarm and runtime use the SAME cache
# (otherwise a differing $HOME on the host causes a cache miss -> runtime fetch).
ENV TECTONIC_CACHE_DIR=/opt/tectonic-cache

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./backend/
WORKDIR /app/backend

# Pre-warm tectonic's package bundle with the SAME packages the resume/cover
# templates use, so the first real PDF compile needs no network and is fast.
RUN printf '%s\n' \
    '\documentclass[10pt,a4paper]{article}' \
    '\usepackage[utf8]{inputenc}' \
    '\usepackage[T1]{fontenc}' \
    '\usepackage[margin=0.5in]{geometry}' \
    '\usepackage{enumitem}' \
    '\usepackage{titlesec}' \
    '\usepackage{hyperref}' \
    '\usepackage{xcolor}' \
    '\setlist[itemize]{itemsep=0pt}' \
    '\begin{document}warmup \textbf{x} \\ y\end{document}' > /tmp/warm.tex \
    && tectonic --outdir /tmp /tmp/warm.tex || true

ENV PYTHONUNBUFFERED=1
EXPOSE 8000
# Render injects $PORT; default to 8000 for local `docker run`.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
