"""JD match score: one LLM call rating how well the library fits the JD (0-100)."""

from __future__ import annotations

import logging
from typing import Optional

from ..llm import LLMClient
from ..llm.prompts.match import MATCH_SYSTEM, MATCH_USER
from ..schemas import MaterialsLibrary

logger = logging.getLogger("resume_tailor.match")


def _background(lib: MaterialsLibrary) -> str:
    lines = []
    if lib.education:
        ed = lib.education[0]
        lines.append(f"Education: {ed.degree} in {ed.major}".strip())
    for e in lib.experiences:
        head = " at ".join(p for p in [e.title, e.organization] if p)
        doms = f" [{', '.join(e.domains)}]" if e.domains else ""
        bullets = " ".join(b.text for b in e.bullets[:3])
        lines.append(f"- {head}{doms}: {bullets}")
    for p in lib.projects:
        head = " at ".join(s for s in [p.title, p.organization] if s)
        doms = f" [{', '.join(p.domains)}]" if p.domains else ""
        bullets = " ".join(b.text for b in p.bullets[:2])
        lines.append(f"- (project) {head}{doms}: {bullets}")
    if lib.skills:
        lines.append("Skills: " + ", ".join(s.name for s in lib.skills[:30] if s.name.strip()))
    return "\n".join(lines) or "(no background provided)"


def score_match(jd_text: str, library: MaterialsLibrary,
                client: Optional[LLMClient] = None) -> dict:
    """Return {'score': int, 'summary': str, 'strengths': [...], 'gaps': [...]}.

    Scores directly from the raw JD text, so it works standalone (no separate
    JD-analysis step required).
    """
    user = MATCH_USER.format(
        jd=(jd_text or "").strip()[:4000] or "(no job description provided)",
        background=_background(library),
    )
    client = client or LLMClient()
    raw = client.complete_json(MATCH_SYSTEM, user, max_tokens=800)
    data = raw if isinstance(raw, dict) else {}

    try:
        score = int(round(float(data.get("score", 0))))
    except (TypeError, ValueError):
        score = 0
    score = max(0, min(100, score))
    strengths = [str(s).strip() for s in (data.get("strengths") or []) if str(s).strip()]
    gaps = [str(g).strip() for g in (data.get("gaps") or []) if str(g).strip()]
    summary = str(data.get("summary") or "").strip()
    logger.info("Match score: %d", score)
    return {"score": score, "summary": summary, "strengths": strengths, "gaps": gaps}
