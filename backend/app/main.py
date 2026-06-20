"""FastAPI application entrypoint.

M1 scope: app skeleton, /health, startup checks (LaTeX engine + API key).
Later milestones add /jd/analyze, /materials, /generate routers.
"""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import Depends, FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse

from .config import get_settings
from .deps import require_auth
from .latex_tools import INSTALL_HINT, detect_latex_engine
from .llm import LLMError
from .routers import auth as auth_router
from .routers import cover_letter as cover_letter_router
from .routers import generate as generate_router
from .routers import jd as jd_router
from .routers import match as match_router
from .routers import materials as materials_router
from .routers import render as render_router
from .routers import rewrite as rewrite_router
from .routers import selection as selection_router

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(name)s | %(message)s")
logger = logging.getLogger("resume_tailor")

STATIC_DIR = Path(__file__).resolve().parent / "static"

app = FastAPI(title="AI Resume Tailor", version="0.1.0")

# Login routes are open; everything else is gated behind the shared login.
app.include_router(auth_router.router)
_auth = [Depends(require_auth)]
app.include_router(jd_router.router, dependencies=_auth)
app.include_router(selection_router.router, dependencies=_auth)
app.include_router(materials_router.router, dependencies=_auth)
app.include_router(rewrite_router.router, dependencies=_auth)
app.include_router(render_router.router, dependencies=_auth)
app.include_router(cover_letter_router.router, dependencies=_auth)
app.include_router(generate_router.router, dependencies=_auth)
app.include_router(match_router.router, dependencies=_auth)


@app.exception_handler(LLMError)
def _llm_error_handler(request: Request, exc: LLMError) -> JSONResponse:
    """Any LLM problem (bad key, low balance, rate limit) -> clear 503 JSON."""
    return JSONResponse(status_code=503, content={"detail": str(exc)})


@app.exception_handler(Exception)
def _unhandled_handler(request: Request, exc: Exception) -> JSONResponse:
    """Never let an unhandled error reach the browser as non-JSON 'Internal Server
    Error' (which the frontend can't parse). Return the message as JSON instead."""
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": f"Server error: {exc}"})


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    """Serve the single-page frontend (zero-build, same-origin)."""
    return FileResponse(STATIC_DIR / "index.html")


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
    using_user_library = settings.materials_path.exists()
    return {
        "status": "ok",
        "version": app.version,
        "latex_engine": engine.name if engine else None,
        "has_api_key": settings.has_api_key,
        "model": settings.model,
        # "user" = your saved materials.json; "sample" = the dev fallback fixture.
        "materials_source": "user" if using_user_library else "sample",
    }
