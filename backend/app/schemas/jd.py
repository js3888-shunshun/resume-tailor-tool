"""Pydantic model for the Job Description (JD) analysis output (Step 2)."""

from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field

from .materials import Category


class JDProfile(BaseModel):
    """Structured profile produced by the LLM after analysing raw JD text."""

    job_title: str
    company: str
    primary_category: Category
    secondary_categories: List[Category] = Field(default_factory=list)
    key_skills: List[str] = Field(default_factory=list)
    key_responsibilities: List[str] = Field(default_factory=list)
    # Concise skill/tool/method nouns suitable for keyword highlighting in the resume.
    keywords_for_highlight: List[str] = Field(default_factory=list)
    # e.g. "startup/casual", "enterprise/formal"
    tone_hints: str = ""
