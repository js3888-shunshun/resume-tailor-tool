"""Router for Step 4: rewrite selected bullets to the JD. `POST /rewrite`.

Takes the user's finalized selection (after any manual add/remove) plus the JD
profile, and returns the same experiences/projects with each bullet's
`rewritten_text` and `matched_keywords` filled.
"""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..llm import LLMError
from ..materials_store import load_materials
from ..pipeline.step4_rewrite import rewrite_selected
from ..pipeline.step4_skills import tailor_skills
from ..schemas import JDProfile, MaterialsLibrary, SelectedExperience, SkillGroup

router = APIRouter(tags=["rewrite"])


class RewriteRequest(BaseModel):
    jd_profile: JDProfile
    selected_experiences: List[SelectedExperience] = Field(default_factory=list)
    selected_projects: List[SelectedExperience] = Field(default_factory=list)
    # Also regroup & JD-tailor the skills section (Polish step does both).
    tailor_skills: bool = True


class RewriteResult(BaseModel):
    selected_experiences: List[SelectedExperience] = Field(default_factory=list)
    selected_projects: List[SelectedExperience] = Field(default_factory=list)
    skill_groups: List[SkillGroup] = Field(default_factory=list)


def _title_context(lib: Optional[MaterialsLibrary]) -> dict:
    """Map source_id -> {title, organization} from the library for prompt context."""
    if lib is None:
        return {}
    ctx: dict = {}
    for e in lib.experiences:
        ctx[e.id] = {"title": e.title, "organization": e.organization}
    for p in lib.projects:
        ctx[p.id] = {"title": p.title, "organization": p.organization}
    return ctx


@router.post("/rewrite", response_model=RewriteResult)
def rewrite(req: RewriteRequest) -> RewriteResult:
    try:
        lib = load_materials()
    except Exception:  # noqa: BLE001
        lib = None
    try:
        exps, projs = rewrite_selected(
            req.jd_profile,
            req.selected_experiences,
            req.selected_projects,
            context=_title_context(lib),
        )
        groups: List[SkillGroup] = []
        if req.tailor_skills and lib is not None:
            groups = tailor_skills(req.jd_profile, lib)
    except LLMError as e:
        raise HTTPException(status_code=503, detail=str(e))
    return RewriteResult(selected_experiences=exps, selected_projects=projs, skill_groups=groups)
