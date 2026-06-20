"""Shared-login auth routes for the deployed app.

A single shared username/password (env APP_USERNAME / APP_PASSWORD) gates the API.
On success we set an HttpOnly session cookie so subsequent fetches AND the PDF
preview iframes (which can't send custom headers) are authorised automatically.
When APP_PASSWORD is unset the app is open (local/dev).
"""

from __future__ import annotations

import hmac
from typing import Optional

from fastapi import APIRouter, Cookie, HTTPException, Request, Response
from pydantic import BaseModel

from ..config import get_settings
from ..deps import SESSION_COOKIE, auth_enabled, check_credentials, session_token

router = APIRouter(tags=["auth"])


class LoginRequest(BaseModel):
    username: str = ""
    password: str = ""


@router.get("/api/auth")
def auth_status(rt_session: Optional[str] = Cookie(default=None)) -> dict:
    """Report whether login is required and whether this browser is already in."""
    s = get_settings()
    signed_in = (not s.app_password) or bool(
        rt_session and hmac.compare_digest(rt_session, session_token(s.app_password))
    )
    return {"auth_required": auth_enabled(), "signed_in": signed_in}


@router.post("/api/login")
def login(req: LoginRequest, request: Request, response: Response) -> dict:
    if not check_credentials(req.username, req.password):
        raise HTTPException(status_code=401, detail="Wrong username or password")
    s = get_settings()
    if s.app_password:
        # Secure cookie over https (prod); plain over http (local dev).
        is_https = request.url.scheme == "https" or request.headers.get("x-forwarded-proto") == "https"
        response.set_cookie(
            SESSION_COOKIE, session_token(s.app_password),
            httponly=True, samesite="lax", secure=is_https, max_age=60 * 60 * 24 * 30, path="/",
        )
    return {"ok": True}


@router.post("/api/logout")
def logout(response: Response) -> dict:
    response.delete_cookie(SESSION_COOKIE, path="/")
    return {"ok": True}
