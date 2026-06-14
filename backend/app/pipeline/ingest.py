"""M3.5: decompose raw resume text into a MaterialsLibrary via the LLM.

Independently testable: inject an LLMClient with a responder to avoid the network.
"""

from __future__ import annotations

import logging
from typing import Optional

from ..llm import LLMClient
from ..llm.prompts.resume_decompose import (
    RESUME_DECOMPOSE_SYSTEM,
    RESUME_DECOMPOSE_USER,
)
from ..schemas import MaterialsLibrary

logger = logging.getLogger("resume_tailor.ingest")


def decompose_resume(resume_text: str, client: Optional[LLMClient] = None) -> MaterialsLibrary:
    if not resume_text or not resume_text.strip():
        raise ValueError("resume_text is empty.")
    client = client or LLMClient()
    user = RESUME_DECOMPOSE_USER.format(resume_text=resume_text.strip())
    # Larger budget: the whole library can be sizable.
    raw = client.complete_json(RESUME_DECOMPOSE_SYSTEM, user, max_tokens=8192)
    library = MaterialsLibrary.model_validate(raw)
    logger.info(
        "Resume decomposed: %d education / %d experiences / %d projects / %d skills",
        len(library.education),
        len(library.experiences),
        len(library.projects),
        len(library.skills),
    )
    return library
