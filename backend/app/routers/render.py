"""Router for Step 5: render the finalized resume to LaTeX. `POST /render`.

Takes the finalized rewrite (selected experiences/projects with `rewritten_bullets`)
plus optional skills, assembles a self-contained `ResumeDocument` by pulling
education / contact / titles / dates from the saved library, and returns the
`.tex`. If a LaTeX engine is installed it also compiles a PDF and exposes it at
`GET /render/pdf`.
"""

from __future__ import annotations

from typing import List, Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from ..config import get_settings
from ..latex_tools import detect_latex_engine
from ..materials_store import load_materials
from ..render.compile import compile_error_of, pdf_to_base64, try_compile
from ..render.fit import fit_to_one_page
from ..render.latex import render_resume
from ..schemas import (
    Education,
    Experience,
    JDProfile,
    MaterialsLibrary,
    Project,
    RenderBullet,
    RenderContact,
    RenderEducation,
    RenderEntry,
    ResumeDocument,
    SelectedExperience,
    SkillGroup,
)

router = APIRouter(tags=["render"])


class RenderRequest(BaseModel):
    jd_profile: Optional[JDProfile] = None
    selected_experiences: List[SelectedExperience] = Field(default_factory=list)
    selected_projects: List[SelectedExperience] = Field(default_factory=list)
    # JD-tailored, labeled skill groups (from Polish). Rendered two-up. If empty,
    # `skills` (or all library skills) is rendered as one flat line.
    skill_groups: List[SkillGroup] = Field(default_factory=list)
    # The selection's chosen skill names; falls back to all library skills if empty.
    skills: List[str] = Field(default_factory=list)
    highlight: bool = True
    projects_heading: str = "Research Experience"
    # Put the projects/research section before professional experience.
    projects_first: bool = False
    # Step 6: auto-tune spacing to land on exactly one page (needs an engine).
    fit_one_page: bool = True
    # The user's library (client-supplied); server file/sample fallback when absent.
    library: Optional[MaterialsLibrary] = None


class RenderResult(BaseModel):
    tex: str
    pdf_available: bool = False
    # The compiled PDF, base64-encoded, returned inline so the browser previews/
    # downloads its OWN result (no shared server file -> safe for many users).
    pdf_base64: Optional[str] = None
    engine: Optional[str] = None
    # When the engine is present but the compile failed, the engine's error tail
    # (for diagnosing server-side compile problems without digging through logs).
    compile_error: Optional[str] = None
    # Step 6 outcome: "fit" (landed on one page), "overflow" (too long even at
    # tightest spacing — trim manually), "no_engine", "error", or None if fit
    # wasn't run. `pages` is the chosen layout's page count.
    fit_status: Optional[str] = None
    pages: Optional[int] = None


def _bullets(group: SelectedExperience) -> List[RenderBullet]:
    """Prefer the finalized rewrite; fall back to the original selected text."""
    source = group.rewritten_bullets or group.selected_bullets
    out: List[RenderBullet] = []
    for b in source:
        text = (b.rewritten_text or b.original_text or "").strip()
        if text:
            out.append(RenderBullet(text=text, keywords=b.matched_keywords))
    return out


def _date_range(start: str, end: str) -> str:
    # LaTeX "--" renders an en-dash; ASCII-safe across engines/encodings.
    parts = [p for p in (start.strip(), end.strip()) if p]
    return " -- ".join(parts)


def _degree_line(ed: Education) -> str:
    degree, major = ed.degree.strip(), ed.major.strip()
    return f"{degree} in {major}" if (major and major.lower() not in degree.lower() and degree) else (degree or major)


def _experience_entry(group: SelectedExperience, exp: Optional[Experience]) -> RenderEntry:
    return RenderEntry(
        organization=exp.organization if exp else "",
        title=exp.title if exp else group.source_id,
        location=exp.location if exp else "",
        date_range=_date_range(exp.start_date, exp.end_date) if exp else "",
        bullets=_bullets(group),
    )


def _project_entry(group: SelectedExperience, proj: Optional[Project]) -> RenderEntry:
    return RenderEntry(
        kind="project",
        organization=proj.organization if proj else "",
        title=proj.title if proj else group.source_id,
        date_range=_date_range(proj.start_date, proj.end_date) if proj else "",
        bullets=_bullets(group),
    )


def _build_document(req: RenderRequest, lib: MaterialsLibrary) -> ResumeDocument:
    exp_by_id = {e.id: e for e in lib.experiences}
    proj_by_id = {p.id: p for p in lib.projects}

    contact = RenderContact(
        name=lib.personal_info.name,
        email=lib.personal_info.email,
        phone=lib.personal_info.phone,
        location=lib.personal_info.location,
        links=lib.personal_info.links,
    )
    education = [
        RenderEducation(
            school=ed.school,
            location=ed.location,
            degree_line=_degree_line(ed),
            gpa=ed.gpa.strip(),
            date=ed.end_date or ed.start_date,
            details=ed.details,
        )
        for ed in lib.education
    ]
    skills = req.skills or [s.name for s in lib.skills]

    experiences = [
        _experience_entry(g, exp_by_id.get(g.source_id)) for g in req.selected_experiences
    ]
    projects = [
        _project_entry(g, proj_by_id.get(g.source_id)) for g in req.selected_projects
    ]

    return ResumeDocument(
        contact=contact,
        education=education,
        skill_groups=req.skill_groups,
        skills=skills,
        experiences=experiences,
        projects=projects,
        projects_heading=req.projects_heading,
        projects_first=req.projects_first,
        highlight=req.highlight,
    )


def build_render_result(req: RenderRequest, lib: MaterialsLibrary) -> RenderResult:
    """Render (and best-effort compile) the resume. Shared by /render and /generate."""
    doc = _build_document(req, lib)
    settings = get_settings()
    engine = detect_latex_engine()
    # Unique stem per request so concurrent users never share a PDF file.
    stem = f"resume_{uuid4().hex}"

    if req.fit_one_page and engine:
        fit = fit_to_one_page(doc, settings.output_dir, stem=stem)
        pdf_path = settings.output_dir / f"{stem}.pdf"
        b64 = pdf_to_base64(pdf_path) if fit.pdf_available else None
        _cleanup(pdf_path)
        # Engine present but no PDF -> capture the compile error for diagnosis.
        err = None if fit.pdf_available else compile_error_of(fit.tex, settings.output_dir)
        return RenderResult(
            tex=fit.tex, pdf_available=fit.pdf_available, pdf_base64=b64,
            engine=engine.name, fit_status=fit.status, pages=fit.pages, compile_error=err,
        )

    # No fit requested (or no engine): single render/compile at default spacing.
    tex = render_resume(doc)
    pdf_path = try_compile(tex, settings.output_dir, stem=stem) if engine else None
    b64 = pdf_to_base64(pdf_path) if pdf_path else None
    _cleanup(pdf_path)
    err = compile_error_of(tex, settings.output_dir) if (engine and not pdf_path) else None
    return RenderResult(
        tex=tex, pdf_available=pdf_path is not None, pdf_base64=b64,
        engine=engine.name if engine else None,
        fit_status="no_engine" if not engine else None, compile_error=err,
    )


def _cleanup(pdf_path) -> None:
    try:
        if pdf_path:
            pdf_path.unlink(missing_ok=True)
    except OSError:
        pass


@router.post("/render", response_model=RenderResult)
def render(req: RenderRequest) -> RenderResult:
    try:
        lib = req.library or load_materials()
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Could not load library: {e}")
    return build_render_result(req, lib)


@router.get("/render/pdf", include_in_schema=True)
def render_pdf() -> FileResponse:
    """Serve the most recently compiled resume PDF, inline so it can preview in an
    iframe. (The UI's Download link forces a download via the `download` attr.)"""
    pdf = get_settings().output_dir / "resume.pdf"
    if not pdf.exists():
        raise HTTPException(status_code=404, detail="No compiled PDF yet (install tectonic/pdflatex, then re-render).")
    return FileResponse(
        pdf,
        media_type="application/pdf",
        content_disposition_type="inline",
        headers={"Cache-Control": "no-store"},
    )
