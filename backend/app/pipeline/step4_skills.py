"""JD-tailored skills step: regroup & prioritize the candidate's skills for the JD.

Pairs with Step 4 (content rewrite): both tailor the selected material to the JD
and feed the finalized draft into rendering. `tailor_skills` makes one LLM call
and returns labeled `SkillGroup`s; it falls back to a single "Skills" group of the
original names if the model returns nothing. Independently testable via an
injected LLMClient responder.
"""

from __future__ import annotations

import json
import logging
from typing import List, Optional

from ..llm import LLMClient
from ..llm.prompts.skills import SKILLS_SYSTEM, SKILLS_USER
from ..schemas import JDProfile, MaterialsLibrary, SkillGroup

logger = logging.getLogger("resume_tailor.skills")


def _coerce_array(raw) -> list:
    if isinstance(raw, list):
        return raw
    if isinstance(raw, dict):
        for v in raw.values():
            if isinstance(v, list):
                return v
    return []


def _fallback(names: List[str]) -> List[SkillGroup]:
    names = [n for n in names if n.strip()]
    return [SkillGroup(label="Skills", skills=names)] if names else []


def tailor_skills(
    jd: JDProfile,
    library: MaterialsLibrary,
    client: Optional[LLMClient] = None,
) -> List[SkillGroup]:
    """Return JD-tailored, labeled skill groups built from the library's skills."""
    inventory = [
        {"name": s.name, "categories": [c.value for c in s.categories]}
        for s in library.skills
        if s.name.strip()
    ]
    all_names = [s["name"] for s in inventory]
    if not inventory:
        return []

    client = client or LLMClient()
    user = SKILLS_USER.format(
        job_title=jd.job_title,
        company=jd.company,
        skills=", ".join(jd.key_skills) or "(none)",
        highlight=", ".join(jd.keywords_for_highlight) or "(none)",
        primary=jd.primary_category,
        secondary=", ".join(jd.secondary_categories) or "(none)",
        inventory=json.dumps(inventory, ensure_ascii=False),
    )
    raw = client.complete_json(SKILLS_SYSTEM, user, max_tokens=2048)

    groups: List[SkillGroup] = []
    for item in _coerce_array(raw):
        if not isinstance(item, dict):
            continue
        label = (item.get("label") or "").strip()
        skills = [str(s).strip() for s in (item.get("skills") or []) if str(s).strip()]
        if label and skills:
            groups.append(SkillGroup(label=label, skills=skills))

    if not groups:
        logger.info("Skills tailoring returned nothing; falling back to flat list.")
        return _fallback(all_names)
    logger.info("Tailored skills into %d groups", len(groups))
    return groups
