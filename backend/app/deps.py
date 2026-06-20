"""Shared FastAPI dependencies for the stateless/public deployment.

Each request carries its own Anthropic API key (header `X-Anthropic-Key`) so the
server holds no secret and every user pays for their own LLM calls. The key falls
back to the server's env var when the header is absent (local/dev use).
"""

from __future__ import annotations

import hashlib
import hmac
from typing import Optional

from fastapi import Cookie, Header, HTTPException

from .config import get_settings
from .llm import LLMClient

SESSION_COOKIE = "rt_session"


def make_client(
    x_anthropic_key: Optional[str] = Header(default=None, alias="X-Anthropic-Key"),
) -> LLMClient:
    """Build an LLMClient from the request's API key (env fallback when absent)."""
    return LLMClient(api_key=x_anthropic_key)


def session_token(password: str) -> str:
    """Deterministic, non-reversible session token derived from the shared password."""
    return hashlib.sha256(("resume-tailor:" + password).encode()).hexdigest()


def auth_enabled() -> bool:
    return bool(get_settings().app_password)


def check_credentials(username: str, password: str) -> bool:
    s = get_settings()
    if not s.app_password:
        return True
    user_ok = (not s.app_username) or hmac.compare_digest(username or "", s.app_username)
    return user_ok and hmac.compare_digest(password or "", s.app_password)


def require_auth(rt_session: Optional[str] = Cookie(default=None)) -> None:
    """Gate API routes behind the shared login (no-op when auth is disabled)."""
    s = get_settings()
    if not s.app_password:
        return
    expected = session_token(s.app_password)
    if not rt_session or not hmac.compare_digest(rt_session, expected):
        raise HTTPException(status_code=401, detail="Not signed in")
