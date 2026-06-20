"""Router for answering application questions. `POST /answer`."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..deps import make_client
from ..llm import LLMClient, LLMError
from ..materials_store import load_materials
from ..pipeline.answer_question import answer_question
from ..schemas import MaterialsLibrary

router = APIRouter(tags=["answer"])


class AnswerRequest(BaseModel):
    question: str
    jd_text: str = ""
    library: Optional[MaterialsLibrary] = None


class AnswerResult(BaseModel):
    answer: str


@router.post("/answer", response_model=AnswerResult)
def answer(req: AnswerRequest, client: LLMClient = Depends(make_client)) -> AnswerResult:
    if not req.question.strip():
        raise HTTPException(status_code=422, detail="Please paste a question first.")
    try:
        lib = req.library or load_materials()
    except (FileNotFoundError, ValueError) as e:
        raise HTTPException(status_code=500, detail=f"Failed to load materials: {e}")
    try:
        text = answer_question(req.question, lib, jd_text=req.jd_text, client=client)
    except LLMError as e:
        raise HTTPException(status_code=503, detail=str(e))
    return AnswerResult(answer=text)
