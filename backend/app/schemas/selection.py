"""Pydantic models for selection & rewrite results (Step 3 / Step 4).

Step 3 produces a *pre-rewrite* selection (which bullets were chosen and why).
Step 4 fills in `rewritten_text` and `matched_keywords`. We reuse the same
container types; pre-rewrite results simply leave the rewrite fields empty.
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class SelectedBullet(BaseModel):
    source_bullet_id: str
    # Original text, carried through so Step 4 / Step 6 can compare lengths.
    original_text: str = ""
    # Relevance score from the Step 3 scoring function (debug / ordering aid).
    score: float = 0.0
    # Filled by Step 4. None until rewritten.
    rewritten_text: Optional[str] = None
    matched_keywords: List[str] = Field(default_factory=list)


class SelectedExperience(BaseModel):
    source_id: str
    # Experience-level relevance: the experience is matched/ranked as a whole
    # (category fit + how many distinct JD keywords it touches across its bullets).
    score: float = 0.0
    matched_keywords: List[str] = Field(default_factory=list)
    # Which JD categories this experience matched, e.g. "MLE (primary)", "AI".
    matched_categories: List[str] = Field(default_factory=list)
    # Score breakdown for transparent "why this score" display.
    category_score: float = 0.0
    keyword_score: float = 0.0
    selected_bullets: List[SelectedBullet] = Field(default_factory=list)
    # Step 4 output: the experience rewritten AS A WHOLE for the JD (may have a
    # different number of bullets than the original — relevant points amplified,
    # weak ones condensed/dropped). Each carries the JD keywords it surfaces.
    rewritten_bullets: List[SelectedBullet] = Field(default_factory=list)


class SelectionResult(BaseModel):
    selected_education: List[str] = Field(default_factory=list)
    selected_experiences: List[SelectedExperience] = Field(default_factory=list)
    selected_projects: List[SelectedExperience] = Field(default_factory=list)
    selected_skills: List[str] = Field(default_factory=list)
    # ALL category-matching candidates, ranked, so the UI can let the user
    # add/swap experiences the auto-selection didn't pick. The default
    # `selected_*` lists are simply the top N of these.
    ranked_experiences: List[SelectedExperience] = Field(default_factory=list)
    ranked_projects: List[SelectedExperience] = Field(default_factory=list)
