"""Step 2: analyse raw JD text into a structured JDProfile.

Single responsibility, schema-typed I/O, independently testable (inject an
LLMClient with a responder to test without the network).
"""

from __future__ import annotations

import logging
from typing import Optional

from ..llm import LLMClient
from ..llm.prompts.jd_analysis import JD_ANALYSIS_SYSTEM, JD_ANALYSIS_USER
from ..schemas import JDProfile

logger = logging.getLogger("resume_tailor.step2")


def analyze_jd(jd_text: str, client: Optional[LLMClient] = None) -> JDProfile:
    if not jd_text or not jd_text.strip():
        raise ValueError("jd_text is empty.")
    client = client or LLMClient()
    user = JD_ANALYSIS_USER.format(jd_text=jd_text.strip())
    raw = client.complete_json(JD_ANALYSIS_SYSTEM, user)
    profile = JDProfile.model_validate(raw)
    logger.info(
        "JD analysed: %s @ %s (primary=%s, %d keywords)",
        profile.job_title,
        profile.company,
        profile.primary_category.value,
        len(profile.keywords_for_highlight),
    )
    return profile
