"""Router for the JD match score. `POST /match`.

Rates how well the candidate's library fits the JD on a 0-100 scale.
"""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..deps import make_client
from ..llm import LLMClient, LLMError
from ..materials_store import load_materials
from ..pipeline.match_score import score_match
from ..schemas import MaterialsLibrary

router = APIRouter(tags=["match"])


class MatchRequest(BaseModel):
    jd_text: str
    library: Optional[MaterialsLibrary] = None


class MatchResult(BaseModel):
    score: int
    summary: str = ""
    strengths: List[str] = Field(default_factory=list)
    gaps: List[str] = Field(default_factory=list)


@router.post("/match", response_model=MatchResult)
def match(req: MatchRequest, client: LLMClient = Depends(make_client)) -> MatchResult:
    try:
        lib = req.library or load_materials()
    except (FileNotFoundError, ValueError) as e:
        raise HTTPException(status_code=500, detail=f"Failed to load materials: {e}")
    try:
        result = score_match(req.jd_text, lib, client=client)
    except LLMError as e:
        raise HTTPException(status_code=503, detail=str(e))
    return MatchResult(**result)
