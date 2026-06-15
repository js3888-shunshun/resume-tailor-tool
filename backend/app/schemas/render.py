"""Schema for Step 5 rendering: a self-contained resume document.

`render_resume()` is a pure function of a `ResumeDocument` — it does NOT reach
into the library or selection result. The `/render` router assembles a
`ResumeDocument` from (library + finalized rewrite) and hands it to the renderer,
keeping the LaTeX layer independently testable.
"""

from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field


class RenderContact(BaseModel):
    name: str
    email: str = ""
    phone: str = ""
    location: str = ""
    links: List[str] = Field(default_factory=list)


class RenderEducation(BaseModel):
    school: str
    location: str = ""
    # e.g. "MEng in Data Science and Decision Analytics, GPA: 3.9/4.0"
    degree_line: str = ""
    date: str = ""  # e.g. "May 2026"
    details: List[str] = Field(default_factory=list)


class RenderBullet(BaseModel):
    text: str
    # JD keywords to wrap in \hlkw within this bullet (subset of `text`).
    keywords: List[str] = Field(default_factory=list)


class RenderEntry(BaseModel):
    """One experience or project. Empty segments are omitted at render time."""

    organization: str = ""
    title: str = ""
    location: str = ""
    date_range: str = ""
    bullets: List[RenderBullet] = Field(default_factory=list)


class ResumeDocument(BaseModel):
    contact: RenderContact
    education: List[RenderEducation] = Field(default_factory=list)
    skills: List[str] = Field(default_factory=list)
    experiences: List[RenderEntry] = Field(default_factory=list)
    projects: List[RenderEntry] = Field(default_factory=list)
    # The user's resume labels this section "Research Experience"; configurable.
    projects_heading: str = "Projects"
    # Wrap matched JD keywords in \hlkw (bold) for ATS emphasis.
    highlight: bool = True
