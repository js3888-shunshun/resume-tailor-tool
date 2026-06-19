"""Router for Step 7: generate a one-page cover letter. `POST /cover-letter`.

Generates the letter body with the LLM (candidate's voice, no AI-tell punctuation),
assembles a `CoverLetterDocument` with contact/date, returns the `.tex`, and
compiles a PDF when a LaTeX engine is present (`GET /cover-letter/pdf`).
"""

from __future__ import annotations

from datetime import date
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from ..config import get_settings
from ..latex_tools import detect_latex_engine
from ..materials_store import load_materials
from ..pipeline.step7_cover_letter import generate_cover_letter
from ..render.compile import count_pages, try_compile
from ..render.cover_letter import render_cover_letter
from ..schemas import (
    CoverLetterDocument,
    JDProfile,
    RenderContact,
    SelectedExperience,
)

router = APIRouter(tags=["cover-letter"])


class CoverLetterRequest(BaseModel):
    jd_profile: JDProfile
    # Optional finalized selection to ground the letter in tailored content.
    selected_experiences: List[SelectedExperience] = Field(default_factory=list)
    selected_projects: List[SelectedExperience] = Field(default_factory=list)
    # Raw JD text + the candidate's company research, used for the "Why this
    # company" paragraph (grounded, not fabricated).
    jd_text: str = ""
    company_notes: str = ""
    # Optional addressee details; omitted from the letter when blank.
    recruiter: str = ""
    company_address: str = ""


class CoverLetterResult(BaseModel):
    tex: str
    salutation: str
    paragraphs: List[str]
    closing: str
    pdf_available: bool = False
    engine: Optional[str] = None
    pages: Optional[int] = None


@router.post("/cover-letter", response_model=CoverLetterResult)
def cover_letter(req: CoverLetterRequest) -> CoverLetterResult:
    try:
        lib = load_materials()
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Could not load library: {e}")

    parts = generate_cover_letter(
        req.jd_profile, lib,
        selected_experiences=req.selected_experiences,
        selected_projects=req.selected_projects,
        jd_text=req.jd_text,
        company_notes=req.company_notes,
    )

    pi = lib.personal_info
    recruiter = req.recruiter.strip()
    # Address the salutation to the recruiter by name when we have one.
    salutation = f"Dear {recruiter}," if recruiter else parts["salutation"]
    doc = CoverLetterDocument(
        contact=RenderContact(name=pi.name, email=pi.email, phone=pi.phone,
                              location=pi.location, links=pi.links),
        date=date.today().strftime("%B %d, %Y"),
        recruiter=recruiter,
        company=req.jd_profile.company,
        company_address=req.company_address.strip(),
        job_title=req.jd_profile.job_title,
        salutation=salutation,
        paragraphs=parts["paragraphs"],
        closing=parts["closing"],
    )
    tex = render_cover_letter(doc)

    settings = get_settings()
    engine = detect_latex_engine()
    pdf = try_compile(tex, settings.output_dir, stem="cover_letter") if engine else None
    return CoverLetterResult(
        tex=tex,
        salutation=salutation,
        paragraphs=doc.paragraphs,
        closing=doc.closing,
        pdf_available=pdf is not None,
        engine=engine.name if engine else None,
        pages=count_pages(pdf) if pdf else None,
    )


@router.get("/cover-letter/pdf", include_in_schema=True)
def cover_letter_pdf() -> FileResponse:
    """Serve the most recently compiled cover letter PDF, inline for preview."""
    pdf = get_settings().output_dir / "cover_letter.pdf"
    if not pdf.exists():
        raise HTTPException(status_code=404, detail="No compiled cover letter yet.")
    return FileResponse(
        pdf, media_type="application/pdf",
        content_disposition_type="inline",
        headers={"Cache-Control": "no-store"},
    )
