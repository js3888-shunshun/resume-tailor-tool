"""Step 7: generate a one-page cover letter in the candidate's voice.

Builds a truthful background summary from the library (focused on the finalized
selection when provided), makes one LLM call, and returns the letter parts. A
sanitiser strips AI-tell punctuation (em/en dashes, parentheses) as a safety net
in case the model slips past the prompt's rules.
"""

from __future__ import annotations

import logging
import re
from typing import List, Optional

from ..llm import LLMClient
from ..llm.prompts.cover_letter import COVER_LETTER_SYSTEM, COVER_LETTER_USER
from ..schemas import JDProfile, MaterialsLibrary, SelectedExperience

logger = logging.getLogger("resume_tailor.step7")


def _sanitize(text: str) -> str:
    """Remove the punctuation that reads as AI-generated, per the user's request."""
    text = text.replace("—", ", ").replace("–", ", ")   # em / en dash -> comma
    text = text.replace("(", "").replace(")", "")          # drop parentheses, keep text
    text = re.sub(r"\s+,", ",", text)                      # tidy " ,"
    text = re.sub(r",\s*,", ",", text)                     # collapse ", ,"
    text = re.sub(r"[ \t]{2,}", " ", text).strip()
    return text


def _background(jd: JDProfile, lib: MaterialsLibrary,
                selected: Optional[List[SelectedExperience]]) -> str:
    """A compact, truthful summary of the candidate for the prompt."""
    exp_by_id = {e.id: e for e in lib.experiences}
    proj_by_id = {p.id: p for p in lib.projects}

    lines: List[str] = []
    pi = lib.personal_info
    lines.append(f"Name: {pi.name}")
    if lib.education:
        ed = lib.education[0]
        deg = f"{ed.degree} in {ed.major}".strip()
        lines.append(f"Education: {deg} at {ed.school}".strip())

    # Prefer the finalized selection (already tailored); else all library items.
    used = False
    if selected:
        for g in selected:
            item = exp_by_id.get(g.source_id) or proj_by_id.get(g.source_id)
            org = getattr(item, "organization", "") if item else ""
            title = getattr(item, "title", "") if item else g.source_id
            bullets = [b.rewritten_text or b.original_text for b in (g.rewritten_bullets or g.selected_bullets)]
            bullets = [b for b in bullets if b]
            head = " at ".join(p for p in [title, org] if p)
            if head or bullets:
                lines.append(f"- {head}: " + " ".join(bullets[:3]))
                used = True
    if not used:
        for e in lib.experiences[:4]:
            head = " at ".join(p for p in [e.title, e.organization] if p)
            bullets = [b.text for b in e.bullets[:2]]
            lines.append(f"- {head}: " + " ".join(bullets))

    if lib.skills:
        lines.append("Skills: " + ", ".join(s.name for s in lib.skills[:20] if s.name.strip()))
    return "\n".join(lines)


def generate_cover_letter(
    jd: JDProfile,
    library: MaterialsLibrary,
    selected_experiences: Optional[List[SelectedExperience]] = None,
    selected_projects: Optional[List[SelectedExperience]] = None,
    jd_text: str = "",
    company_notes: str = "",
    client: Optional[LLMClient] = None,
) -> dict:
    """Return {'salutation', 'paragraphs': [...], 'closing'} for the cover letter.

    `company_notes` (the candidate's research / people they've spoken with) and the
    raw `jd_text` ground the all-important "Why this company" paragraph.
    """
    selected = list(selected_experiences or []) + list(selected_projects or [])
    user = COVER_LETTER_USER.format(
        job_title=jd.job_title or "the role",
        company=jd.company or "your company",
        responsibilities="; ".join(jd.key_responsibilities) or "(not specified)",
        skills=", ".join(jd.key_skills) or "(not specified)",
        tone=jd.tone_hints or "professional, warm, sincere",
        company_notes=company_notes.strip() or "(none provided)",
        jd_text=(jd_text or "").strip()[:2000] or "(not provided)",
        background=_background(jd, library, selected),
    )
    client = client or LLMClient()
    raw = client.complete_json(COVER_LETTER_SYSTEM, user, max_tokens=1500)
    data = raw if isinstance(raw, dict) else {}

    paragraphs = [_sanitize(str(p)) for p in (data.get("paragraphs") or []) if str(p).strip()]
    salutation = _sanitize(str(data.get("salutation") or "Dear Hiring Manager,"))
    closing = _sanitize(str(data.get("closing") or "Sincerely,"))
    logger.info("Cover letter generated: %d paragraphs", len(paragraphs))
    return {"salutation": salutation, "paragraphs": paragraphs, "closing": closing}
