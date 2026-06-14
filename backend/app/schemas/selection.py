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
    selected_bullets: List[SelectedBullet] = Field(default_factory=list)


class SelectionResult(BaseModel):
    selected_education: List[str] = Field(default_factory=list)
    selected_experiences: List[SelectedExperience] = Field(default_factory=list)
    selected_projects: List[SelectedExperience] = Field(default_factory=list)
    selected_skills: List[str] = Field(default_factory=list)
