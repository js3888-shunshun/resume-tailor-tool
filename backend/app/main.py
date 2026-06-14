"""FastAPI application entrypoint.

M1 scope: app skeleton, /health, startup checks (LaTeX engine + API key).
Later milestones add /jd/analyze, /materials, /generate routers.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI

from .config import get_settings
from .latex_tools import INSTALL_HINT, detect_latex_engine

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(name)s | %(message)s")
logger = logging.getLogger("resume_tailor")

app = FastAPI(title="AI Resume Tailor", version="0.1.0")


@app.on_event("startup")
def startup_checks() -> None:
    settings = get_settings()

    engine = detect_latex_engine()
    if engine:
        logger.info("LaTeX engine detected: %s (%s)", engine.name, engine.path)
    else:
        logger.warning(INSTALL_HINT)

    if settings.has_api_key:
        logger.info("ANTHROPIC_API_KEY found. Model: %s", settings.model)
    else:
        logger.warning(
            "ANTHROPIC_API_KEY not set. JD analysis / rewrite / cover letter "
            "(Step 2/4/7) will fail until it is configured in .env."
        )


@app.get("/health")
def health() -> dict:
    settings = get_settings()
    engine = detect_latex_engine()
    return {
        "status": "ok",
        "version": app.version,
        "latex_engine": engine.name if engine else None,
        "has_api_key": settings.has_api_key,
        "model": settings.model,
    }
