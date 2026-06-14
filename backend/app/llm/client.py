"""Centralized LLM client. ALL Anthropic calls go through here (ROADMAP rule).

Designed for testability: pass a `responder` callable to bypass the real API
(used by unit tests and for running the pipeline before a key is configured).
"""

from __future__ import annotations

import json
import re
from typing import Callable, Optional

from ..config import get_settings

# A responder takes (system_prompt, user_prompt) and returns the raw model text.
Responder = Callable[[str, str], str]


class LLMError(RuntimeError):
    pass


class LLMClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        responder: Optional[Responder] = None,
        max_retries: int = 2,
    ):
        settings = get_settings()
        self.api_key = api_key if api_key is not None else settings.anthropic_api_key
        self.model = model or settings.model
        self.max_retries = max_retries
        # If a responder is injected we never touch the network (test/mock mode).
        self._responder = responder
        self._client = None  # lazy real client

    # ---- low level -------------------------------------------------------
    def _real_call(self, system: str, user: str, max_tokens: int) -> str:
        if not self.api_key:
            raise LLMError(
                "ANTHROPIC_API_KEY not configured. Set it in .env or inject a "
                "responder for testing."
            )
        if self._client is None:
            import anthropic  # imported lazily so tests don't require the package at import time

            self._client = anthropic.Anthropic(api_key=self.api_key)
        resp = self._client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return "".join(block.text for block in resp.content if block.type == "text")

    def complete(self, system: str, user: str, max_tokens: int = 2048) -> str:
        if self._responder is not None:
            return self._responder(system, user)
        return self._real_call(system, user, max_tokens)

    # ---- JSON helper -----------------------------------------------------
    def complete_json(self, system: str, user: str, max_tokens: int = 2048) -> dict | list:
        """Call the model and parse its reply as JSON, retrying on parse errors."""
        last_err: Optional[Exception] = None
        for attempt in range(self.max_retries + 1):
            raw = self.complete(system, user, max_tokens)
            try:
                return _extract_json(raw)
            except (json.JSONDecodeError, ValueError) as e:
                last_err = e
                # On retry, nudge the model to emit valid JSON only.
                user = (
                    f"{user}\n\nYour previous reply was not valid JSON. "
                    "Reply with ONLY the JSON object, no prose, no code fences."
                )
        raise LLMError(f"Failed to parse JSON after retries: {last_err}")


def _extract_json(text: str) -> dict | list:
    """Extract a JSON object/array from model output, tolerating code fences."""
    s = text.strip()
    # Strip ```json ... ``` or ``` ... ``` fences.
    fence = re.match(r"^```(?:json)?\s*(.*?)\s*```$", s, re.DOTALL)
    if fence:
        s = fence.group(1).strip()
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        # Fall back to the first {...} or [...] span.
        match = re.search(r"(\{.*\}|\[.*\])", s, re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(1))
