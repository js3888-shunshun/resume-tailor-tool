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

from ..schemas import Bullet, Experience, JDProfile, Project


@dataclass
class BulletScore:
    score: float
    # Which JD highlight/skill keywords this bullet hit (for "why selected" UI
    # and as a head start for Step 4; Step 4 may refine this).
    matched_keywords: List[str] = field(default_factory=list)


@dataclass
class ExperienceScore:
    score: float
    # Distinct JD keywords this experience touches across all its bullets.
    matched_keywords: List[str] = field(default_factory=list)
    # Which JD categories this experience matched, e.g. "MLE (primary)", "AI".
    matched_categories: List[str] = field(default_factory=list)
    # Breakdown of the total score, for transparent "why this score" UI.
    category_score: float = 0.0
    keyword_score: float = 0.0
    # bullet id -> keywords it matched (kept for later highlighting in Step 4).
    bullet_matches: dict = field(default_factory=dict)


# Scorers are callables with these shapes. Swap freely (e.g. embeddings later).
Scorer = Callable[[Bullet, JDProfile], BulletScore]
ExperienceScorer = Callable[["Experience | Project", JDProfile], ExperienceScore]


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


def score_experience(
    item: "Experience | Project",
    jd: JDProfile,
    *,
    primary_weight: float = 3.0,
    secondary_weight: float = 1.0,
    highlight_weight: float = 2.0,
    skill_weight: float = 1.0,
) -> ExperienceScore:
    """Score an experience/project AS A WHOLE against the JD.

    Two ingredients:
      1. Category fit: primary category match is worth more than secondaries.
      2. Keyword breadth: distinct JD keywords the experience touches across all
         its bullets (highlight keywords weighted higher than general skills).
    Bullets are NOT scored or ranked individually here — the experience is the
    unit of selection. Per-bullet matches are still recorded for later highlighting.
    """
    cats = set(item.categories)
    cat_score = 0.0
    matched_categories: List[str] = []
    if jd.primary_category in cats:
        cat_score += primary_weight
        matched_categories.append(f"{jd.primary_category.value} (primary)")
    for sec in jd.secondary_categories:
        if sec in cats:
            cat_score += secondary_weight
            matched_categories.append(sec.value)

    highlight_set = {k.lower() for k in jd.keywords_for_highlight}
    matched: List[str] = []
    seen: set[str] = set()
    bullet_matches: dict = {}
    for b in item.bullets:
        bs = score_bullet(b, jd, highlight_weight=highlight_weight, skill_weight=skill_weight)
        bullet_matches[b.id] = bs.matched_keywords
        for kw in bs.matched_keywords:
            if kw.lower() not in seen:
                seen.add(kw.lower())
                matched.append(kw)

    kw_score = sum(highlight_weight if m.lower() in highlight_set else skill_weight for m in matched)
    return ExperienceScore(
        score=cat_score + kw_score,
        matched_keywords=matched,
        matched_categories=matched_categories,
        category_score=cat_score,
        keyword_score=kw_score,
        bullet_matches=bullet_matches,
    )
