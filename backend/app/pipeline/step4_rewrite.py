"""Step 4: rewrite the selected bullets to match the JD.

Batches ALL selected bullets into a single LLM call (one request, JSON array back)
to minimise calls. Mutates the passed SelectedExperience objects in place, filling
`rewritten_text` and `matched_keywords` on each bullet. Independently testable via
an injected LLMClient responder.
"""

from __future__ import annotations

import json
import logging
from typing import List, Optional, Tuple

from ..llm import LLMClient
from ..llm.prompts.rewrite import REWRITE_SYSTEM, REWRITE_USER
from ..schemas import JDProfile, SelectedBullet, SelectedExperience

logger = logging.getLogger("resume_tailor.step4")


def _coerce_array(raw) -> list:
    """Accept a JSON array, or a dict wrapping one (e.g. {"bullets": [...]})."""
    if isinstance(raw, list):
        return raw
    if isinstance(raw, dict):
        for v in raw.values():
            if isinstance(v, list):
                return v
    return []


def rewrite_selected(
    jd: JDProfile,
    experiences: List[SelectedExperience],
    projects: List[SelectedExperience],
    client: Optional[LLMClient] = None,
) -> Tuple[List[SelectedExperience], List[SelectedExperience]]:
    """Fill rewritten_text / matched_keywords on every selected bullet."""
    # Collect bullets with stable temp ids, keeping references for write-back.
    refs: List[Tuple[SelectedBullet, str]] = []
    payload: List[dict] = []
    for group in [*experiences, *projects]:
        for b in group.selected_bullets:
            tid = f"b{len(refs)}"
            refs.append((b, tid))
            payload.append({"id": tid, "text": b.original_text or ""})

    if not payload:
        return experiences, projects

    client = client or LLMClient()
    user = REWRITE_USER.format(
        job_title=jd.job_title,
        company=jd.company,
        highlight=", ".join(jd.keywords_for_highlight) or "(none)",
        skills=", ".join(jd.key_skills) or "(none)",
        bullets=json.dumps(payload, ensure_ascii=False),
    )
    raw = client.complete_json(REWRITE_SYSTEM, user, max_tokens=4096)
    by_id = {r["id"]: r for r in _coerce_array(raw) if isinstance(r, dict) and "id" in r}

    rewritten_count = 0
    for bullet, tid in refs:
        item = by_id.get(tid)
        if not item:
            # Fall back to the original text so nothing is dropped.
            bullet.rewritten_text = bullet.original_text
            continue
        bullet.rewritten_text = (item.get("rewritten_text") or bullet.original_text).strip()
        kws = item.get("matched_keywords") or []
        bullet.matched_keywords = [k for k in kws if isinstance(k, str)]
        rewritten_count += 1

    logger.info("Rewrote %d/%d bullets", rewritten_count, len(refs))
    return experiences, projects
