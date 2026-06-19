"""Pydantic models for the materials library (`materials.json`).

These are the atomic, decomposed experiences/skills extracted from the user's
existing resumes. In Phase 1 the file is hand-authored; later we may add an
"upload resume -> LLM auto-decompose" helper (see ROADMAP Backlog).
"""

from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class Category(str, Enum):
    """Fixed enumeration mapping items to resume variants."""

    AI = "AI"
    DS = "DS"
    DE = "DE"
    MLE = "MLE"
    SDE = "SDE"


class PersonalInfo(BaseModel):
    name: str
    email: str
    phone: str
    location: str = ""
    # Current address, shown on its own line under the resume contact info.
    current_address: str = ""
    links: List[str] = Field(default_factory=list)


class Education(BaseModel):
    id: str
    school: str
    degree: str
    major: str
    location: str = ""
    gpa: str = ""
    start_date: str
    end_date: str
    details: List[str] = Field(default_factory=list)


class Bullet(BaseModel):
    id: str
    text: str
    skill_tags: List[str] = Field(default_factory=list)
    # Free-form metric string, or null if the bullet has no quantified impact.
    impact_metrics: Optional[str] = None
    # Higher priority bullets are kept first when content must be trimmed.
    priority: int = 1


class Experience(BaseModel):
    id: str
    title: str
    organization: str
    location: str = ""
    start_date: str = ""
    end_date: str = ""
    categories: List[Category] = Field(default_factory=list)
    bullets: List[Bullet] = Field(default_factory=list)


class Project(BaseModel):
    id: str
    title: str
    organization: str = ""
    start_date: str = ""
    end_date: str = ""
    categories: List[Category] = Field(default_factory=list)
    bullets: List[Bullet] = Field(default_factory=list)


class Skill(BaseModel):
    name: str
    categories: List[Category] = Field(default_factory=list)
    proficiency: str = ""


class MaterialsLibrary(BaseModel):
    personal_info: PersonalInfo
    education: List[Education] = Field(default_factory=list)
    experiences: List[Experience] = Field(default_factory=list)
    projects: List[Project] = Field(default_factory=list)
    skills: List[Skill] = Field(default_factory=list)
