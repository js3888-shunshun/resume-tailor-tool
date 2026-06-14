"""Router for Step 3: experience selection. `POST /select`.

Takes a JDProfile (the output of /jd/analyze) plus an optional bullet target,
loads the material library, and returns a pre-rewrite SelectionResult.
Kept separate from /jd/analyze so each pipeline step stays independently callable.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..materials_store import load_materials
from ..pipeline.step3_selection import (
    DEFAULT_TARGET_EXPERIENCES,
    DEFAULT_TARGET_PROJECTS,
    select_experiences,
)
from ..schemas import JDProfile, SelectionResult

router = APIRouter(tags=["selection"])


class SelectRequest(BaseModel):
    jd_profile: JDProfile
    # Number of whole experiences / projects (sections) to keep.
    target_experiences: int = Field(default=DEFAULT_TARGET_EXPERIENCES, ge=0, le=15)
    target_projects: int = Field(default=DEFAULT_TARGET_PROJECTS, ge=0, le=15)


@router.post("/select", response_model=SelectionResult)
def select(req: SelectRequest) -> SelectionResult:
    try:
        library = load_materials()
    except (FileNotFoundError, ValueError) as e:
        raise HTTPException(status_code=500, detail=f"Failed to load materials: {e}")
    return select_experiences(
        req.jd_profile,
        library,
        target_experiences=req.target_experiences,
        target_projects=req.target_projects,
    )
