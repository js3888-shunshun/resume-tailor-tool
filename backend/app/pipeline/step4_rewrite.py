"""Step 4: rewrite each selected experience AS A WHOLE to match the JD.

Unlike a 1:1 bullet rewrite, the LLM sees each experience's full bullet set plus
the JD and returns a tailored set of bullets — amplifying JD-relevant points,
condensing/dropping weak ones, surfacing JD keywords for ATS, using strong action
verbs, quantifying where the original supports it (never fabricating). The result
is written to each experience's `rewritten_bullets` (the original `selected_bullets`
are kept so the UI can show before -> after). One batched LLM call for all
experiences. Independently testable via an injected LLMClient responder.
"""

from __future__ import annotations

import json
import logging
from typing import Dict, List, Optional, Tuple

from ..llm import LLMClient
from ..llm.prompts.rewrite import REWRITE_SYSTEM, REWRITE_USER
from ..schemas import JDProfile, SelectedBullet, SelectedExperience

logger = logging.getLogger("resume_tailor.step4")


def _coerce_array(raw) -> list:
    if isinstance(raw, list):
        return raw
    if isinstance(raw, dict):
        for v in raw.values():
            if isinstance(v, list):
                return v
    return []


def _fallback_bullets(group: SelectedExperience) -> List[SelectedBullet]:
    """If the model returns nothing for an experience, keep its originals."""
    return [
        SelectedBullet(
            source_bullet_id=b.source_bullet_id,
            rewritten_text=b.original_text,
            matched_keywords=b.matched_keywords,
        )
        for b in group.selected_bullets
    ]


def rewrite_selected(
    jd: JDProfile,
    experiences: List[SelectedExperience],
    projects: List[SelectedExperience],
    context: Optional[Dict[str, dict]] = None,
    client: Optional[LLMClient] = None,
) -> Tuple[List[SelectedExperience], List[SelectedExperience]]:
    """Fill `rewritten_bullets` on each experience/project (whole-experience rewrite).

    `context` maps source_id -> {"title", "organization"} to give the model the
    role context; optional (falls back to the source_id).
    """
    context = context or {}
    groups = [*experiences, *projects]

    refs: List[Tuple[SelectedExperience, str]] = []
    payload: List[dict] = []
    for group in groups:
        if not group.selected_bullets:
            continue
        tid = f"e{len(refs)}"
        refs.append((group, tid))
        ctx = context.get(group.source_id, {})
        payload.append(
            {
                "id": tid,
                "title": ctx.get("title", group.source_id),
                "organization": ctx.get("organization", ""),
                "bullets": [b.original_text or "" for b in group.selected_bullets],
            }
        )

    if not payload:
        return experiences, projects

    client = client or LLMClient()
    user = REWRITE_USER.format(
        job_title=jd.job_title,
        company=jd.company,
        responsibilities="; ".join(jd.key_responsibilities) or "(none listed)",
        highlight=", ".join(jd.keywords_for_highlight) or "(none)",
        skills=", ".join(jd.key_skills) or "(none)",
        experiences=json.dumps(payload, ensure_ascii=False),
    )
    raw = client.complete_json(REWRITE_SYSTEM, user, max_tokens=4096)
    by_id = {r["id"]: r for r in _coerce_array(raw) if isinstance(r, dict) and "id" in r}

    rewritten_groups = 0
    for group, tid in refs:
        item = by_id.get(tid)
        bullets = item.get("bullets") if isinstance(item, dict) else None
        if not bullets:
            group.rewritten_bullets = _fallback_bullets(group)
            continue
        out: List[SelectedBullet] = []
        for b in bullets:
            if isinstance(b, dict):
                text = (b.get("text") or "").strip()
                kws = [k for k in (b.get("matched_keywords") or []) if isinstance(k, str)]
            else:
                text, kws = str(b).strip(), []
            if text:
                out.append(SelectedBullet(source_bullet_id="", rewritten_text=text, matched_keywords=kws))
        group.rewritten_bullets = out or _fallback_bullets(group)
        rewritten_groups += 1

    logger.info("Rewrote %d/%d experiences", rewritten_groups, len(refs))
    return experiences, projects
