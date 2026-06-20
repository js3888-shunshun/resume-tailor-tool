"""Router for Step 8: one-click end-to-end generation. `POST /generate`.

Chains the whole pipeline — analyze JD, select experiences, rewrite + tailor
skills, render the one-page resume, and write the cover letter — by composing the
existing per-step endpoint functions, so behaviour stays identical to running the
tabs by hand. Returns the intermediate results plus both compiled PDFs (served at
`GET /render/pdf` and `GET /cover-letter/pdf`).
"""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..deps import make_client
from ..llm import LLMClient, LLMError
from ..materials_store import load_materials
from ..pipeline.step2_jd_analysis import analyze_jd
from ..pipeline.step3_selection import (
    DEFAULT_TARGET_EXPERIENCES,
    DEFAULT_TARGET_PROJECTS,
    select_experiences,
)
from ..pipeline.step4_rewrite import rewrite_selected
from ..pipeline.step4_skills import tailor_skills
from ..schemas import (
    JDProfile,
    MaterialsLibrary,
    SelectedExperience,
    SelectionResult,
    SkillGroup,
)
from .cover_letter import CoverLetterRequest, CoverLetterResult, build_cover_result
from .render import RenderRequest, RenderResult, build_render_result
from .rewrite import _title_context

router = APIRouter(tags=["generate"])


class GenerateRequest(BaseModel):
    jd_text: str
    # The user's library (client-supplied); server file/sample fallback when absent.
    library: Optional[MaterialsLibrary] = None
    target_experiences: int = Field(default=DEFAULT_TARGET_EXPERIENCES, ge=0, le=15)
    target_projects: int = Field(default=DEFAULT_TARGET_PROJECTS, ge=0, le=15)
    highlight: bool = True
    fit_one_page: bool = True
    projects_heading: str = "Research Experience"
    projects_first: bool = False
    # Cover letter (optional) + its personalization.
    cover_letter: bool = True
    company_notes: str = ""
    recruiter: str = ""
    company_address: str = ""


class GenerateResult(BaseModel):
    profile: JDProfile
    selection: SelectionResult
    selected_experiences: List[SelectedExperience]
    selected_projects: List[SelectedExperience]
    skill_groups: List[SkillGroup]
    resume: RenderResult
    cover: Optional[CoverLetterResult] = None


@router.post("/generate", response_model=GenerateResult)
def generate(req: GenerateRequest, client: LLMClient = Depends(make_client)) -> GenerateResult:
    # Step 2: analyze the JD.
    try:
        profile = analyze_jd(req.jd_text, client=client)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except LLMError as e:
        raise HTTPException(status_code=503, detail=str(e))

    try:
        lib = req.library or load_materials()
    except (FileNotFoundError, ValueError) as e:
        raise HTTPException(status_code=500, detail=f"Failed to load materials: {e}")

    # Step 3: select whole experiences/projects.
    selection = select_experiences(
        profile, lib,
        target_experiences=req.target_experiences,
        target_projects=req.target_projects,
    )

    # Step 4: rewrite the selection + tailor skills.
    try:
        exps, projs = rewrite_selected(
            profile,
            selection.selected_experiences,
            selection.selected_projects,
            context=_title_context(lib),
            client=client,
        )
        groups = tailor_skills(profile, lib, client=client)
    except LLMError as e:
        raise HTTPException(status_code=503, detail=str(e))

    # Steps 5-6: render the one-page resume.
    resume = build_render_result(RenderRequest(
        jd_profile=profile,
        selected_experiences=exps,
        selected_projects=projs,
        skill_groups=groups,
        skills=selection.selected_skills,
        highlight=req.highlight,
        fit_one_page=req.fit_one_page,
        projects_heading=req.projects_heading,
        projects_first=req.projects_first,
    ), lib)

    # Step 7: cover letter.
    cover = None
    if req.cover_letter:
        cover = build_cover_result(CoverLetterRequest(
            jd_profile=profile,
            selected_experiences=exps,
            selected_projects=projs,
            jd_text=req.jd_text,
            company_notes=req.company_notes,
            recruiter=req.recruiter,
            company_address=req.company_address,
        ), lib, client)

    return GenerateResult(
        profile=profile,
        selection=selection,
        selected_experiences=exps,
        selected_projects=projs,
        skill_groups=groups,
        resume=resume,
        cover=cover,
    )
