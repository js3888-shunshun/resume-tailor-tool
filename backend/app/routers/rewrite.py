"""Router for Step 4: rewrite selected bullets to the JD. `POST /rewrite`.

Takes the user's finalized selection (after any manual add/remove) plus the JD
profile, and returns the same experiences/projects with each bullet's
`rewritten_text` and `matched_keywords` filled.
"""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..llm import LLMError
from ..materials_store import load_materials
from ..pipeline.step4_rewrite import rewrite_selected
from ..schemas import JDProfile, SelectedExperience

router = APIRouter(tags=["rewrite"])


class RewriteRequest(BaseModel):
    jd_profile: JDProfile
    selected_experiences: List[SelectedExperience] = Field(default_factory=list)
    selected_projects: List[SelectedExperience] = Field(default_factory=list)


class RewriteResult(BaseModel):
    selected_experiences: List[SelectedExperience] = Field(default_factory=list)
    selected_projects: List[SelectedExperience] = Field(default_factory=list)


def _title_context() -> dict:
    """Map source_id -> {title, organization} from the saved library for prompt context."""
    try:
        lib = load_materials()
    except Exception:  # noqa: BLE001
        return {}
    ctx: dict = {}
    for e in lib.experiences:
        ctx[e.id] = {"title": e.title, "organization": e.organization}
    for p in lib.projects:
        ctx[p.id] = {"title": p.title, "organization": ""}
    return ctx


@router.post("/rewrite", response_model=RewriteResult)
def rewrite(req: RewriteRequest) -> RewriteResult:
    try:
        exps, projs = rewrite_selected(
            req.jd_profile,
            req.selected_experiences,
            req.selected_projects,
            context=_title_context(),
        )
    except LLMError as e:
        raise HTTPException(status_code=503, detail=str(e))
    return RewriteResult(selected_experiences=exps, selected_projects=projs)
