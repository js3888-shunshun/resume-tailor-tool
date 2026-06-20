"""Answer an application question from the candidate's library (one LLM call)."""

from __future__ import annotations

import logging
from typing import Optional

from ..llm import LLMClient
from ..llm.prompts.app_question import ANSWER_SYSTEM, ANSWER_USER
from ..schemas import MaterialsLibrary
from .match_score import _background

logger = logging.getLogger("resume_tailor.answer")


def _sanitize(text: str) -> str:
    """Light cleanup: drop em/en dashes (the clearest AI tell) and trim."""
    return text.replace("—", ", ").replace("–", ", ").strip()


def answer_question(question: str, library: MaterialsLibrary, jd_text: str = "",
                    client: Optional[LLMClient] = None) -> str:
    jd = (jd_text or "").strip()
    jd_block = f"ROLE / JOB DESCRIPTION (for context):\n{jd[:2500]}\n\n" if jd else ""
    user = ANSWER_USER.format(
        question=question.strip(),
        jd_block=jd_block,
        background=_background(library),
    )
    client = client or LLMClient()
    text = client.complete(ANSWER_SYSTEM, user, max_tokens=1200)
    logger.info("Answered an application question (%d chars)", len(text or ""))
    return _sanitize(text or "")
