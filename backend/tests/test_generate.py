"""Step 8 tests: /generate orchestration wiring (LLM + render stubbed)."""

from __future__ import annotations

import app.routers.generate as gen
from app.routers.cover_letter import CoverLetterResult
from app.routers.generate import GenerateRequest, generate
from app.routers.render import RenderResult
from app.schemas import (
    JDProfile,
    MaterialsLibrary,
    PersonalInfo,
    SelectedBullet,
    SelectedExperience,
    SelectionResult,
    SkillGroup,
)


def _wire(monkeypatch):
    profile = JDProfile(job_title="MLE", company="Globex", primary_category="MLE",
                        key_skills=["Python"])
    exps = [SelectedExperience(source_id="e1", rewritten_bullets=[
        SelectedBullet(source_bullet_id="b1", rewritten_text="did a thing")])]
    projs = []
    groups = [SkillGroup(label="ML", skills=["PyTorch"])]
    selection = SelectionResult(selected_experiences=exps, selected_skills=["Python"])
    lib = MaterialsLibrary(personal_info=PersonalInfo(name="Joy", email="j@x.com", phone="1"))

    captured = {}
    monkeypatch.setattr(gen, "analyze_jd", lambda t, client=None: profile)
    monkeypatch.setattr(gen, "load_materials", lambda: lib)
    monkeypatch.setattr(gen, "select_experiences", lambda p, l, **k: selection)
    monkeypatch.setattr(gen, "rewrite_selected", lambda *a, **k: (exps, projs))
    monkeypatch.setattr(gen, "tailor_skills", lambda *a, **k: groups)

    def fake_render(req, lib):
        captured["render"] = req
        return RenderResult(tex="RESUME", pdf_available=True, engine="tectonic",
                            fit_status="fit", pages=1)

    def fake_cover(req, lib, client):
        captured["cover"] = req
        return CoverLetterResult(tex="COVER", salutation="Dear Hiring Manager,",
                                 paragraphs=["p"], closing="Sincerely,",
                                 pdf_available=True, engine="tectonic", pages=1)

    monkeypatch.setattr(gen, "build_render_result", fake_render)
    monkeypatch.setattr(gen, "build_cover_result", fake_cover)
    return profile, exps, groups, captured


def test_generate_chains_rewrite_into_render_and_cover(monkeypatch):
    profile, exps, groups, captured = _wire(monkeypatch)
    res = generate(GenerateRequest(jd_text="some JD", company_notes="met Jane Li"))

    # rewritten experiences + tailored skills flow into the resume render
    assert captured["render"].selected_experiences == exps
    assert captured["render"].skill_groups == groups
    assert captured["render"].jd_profile == profile
    # same experiences + JD text + notes flow into the cover letter
    assert captured["cover"].selected_experiences == exps
    assert captured["cover"].jd_text == "some JD"
    assert captured["cover"].company_notes == "met Jane Li"
    # result bundles everything
    assert res.resume.tex == "RESUME" and res.resume.pages == 1
    assert res.cover.tex == "COVER"
    assert res.skill_groups == groups


def test_generate_can_skip_cover_letter(monkeypatch):
    _, _, _, captured = _wire(monkeypatch)
    res = generate(GenerateRequest(jd_text="some JD", cover_letter=False))
    assert res.cover is None
    assert "cover" not in captured  # cover endpoint not called
