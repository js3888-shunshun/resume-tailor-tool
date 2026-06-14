"""Relevance scoring for bullets vs a JD profile (Step 3).

ISOLATED ON PURPOSE: this is the piece we expect to swap later for an
embedding-based semantic similarity scorer. Anything matching the
`Scorer` signature `(Bullet, JDProfile) -> BulletScore` can be dropped in.
Phase 1 uses simple keyword overlap.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable, List

from ..schemas import Bullet, JDProfile


@dataclass
class BulletScore:
    score: float
    # Which JD highlight/skill keywords this bullet hit (for "why selected" UI
    # and as a head start for Step 4; Step 4 may refine this).
    matched_keywords: List[str] = field(default_factory=list)


# A scorer is any callable with this shape. Swap freely.
Scorer = Callable[[Bullet, JDProfile], BulletScore]


def _contains_keyword(haystack: str, keyword: str) -> bool:
    """Whole-word-ish containment, case-insensitive.

    Uses word boundaries so "ML" doesn't match "HTML" and "Spark" doesn't match
    "Sparkle", while still allowing multi-word keywords like "A/B testing".
    """
    kw = re.escape(keyword.strip().lower())
    if not kw:
        return False
    return re.search(rf"(?<!\w){kw}(?!\w)", haystack) is not None


def score_bullet(
    bullet: Bullet,
    jd: JDProfile,
    *,
    highlight_weight: float = 2.0,
    skill_weight: float = 1.0,
) -> BulletScore:
    """Keyword-overlap score.

    A keyword counts if it appears in the bullet's `skill_tags` OR its text.
    `keywords_for_highlight` are weighted higher than general `key_skills`
    because they are the terms we most want surfaced on the resume.
    """
    tag_blob = " ".join(bullet.skill_tags).lower()
    text_blob = bullet.text.lower()

    score = 0.0
    matched: List[str] = []

    # Highlight keywords (higher weight).
    for kw in jd.keywords_for_highlight:
        if _contains_keyword(tag_blob, kw) or _contains_keyword(text_blob, kw):
            score += highlight_weight
            matched.append(kw)

    # General key skills (lower weight). Avoid double counting a term already
    # matched as a highlight keyword.
    matched_lower = {m.lower() for m in matched}
    for kw in jd.key_skills:
        if kw.lower() in matched_lower:
            continue
        if _contains_keyword(tag_blob, kw) or _contains_keyword(text_blob, kw):
            score += skill_weight
            matched.append(kw)

    return BulletScore(score=score, matched_keywords=matched)
