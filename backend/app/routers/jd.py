"""Router for JD analysis (Step 2). `POST /jd/analyze` for preview/debugging."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..llm import LLMError
from ..pipeline.step2_jd_analysis import analyze_jd
from ..schemas import JDProfile

router = APIRouter(prefix="/jd", tags=["jd"])


class JDAnalyzeRequest(BaseModel):
    jd_text: str


@router.post("/analyze", response_model=JDProfile)
def analyze(req: JDAnalyzeRequest) -> JDProfile:
    try:
        return analyze_jd(req.jd_text)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except LLMError as e:
        # Missing key / parse failure -> clear client-facing error.
        raise HTTPException(status_code=503, detail=str(e))
