"""Tests for the JD-tailored skills step (mock LLM responder)."""

from __future__ import annotations

import json

from app.llm import LLMClient
from app.pipeline.step4_skills import tailor_skills
from app.schemas import Category, MaterialsLibrary, PersonalInfo, Skill


def _jd():
    from app.schemas import JDProfile
    return JDProfile.model_validate({
        "job_title": "MLE", "company": "Acme", "primary_category": "MLE",
        "key_skills": ["Python", "PyTorch"], "keywords_for_highlight": ["PyTorch"],
    })


def _lib(skill_names):
    return MaterialsLibrary(
        personal_info=PersonalInfo(name="J", email="e", phone="p"),
        skills=[Skill(name=n, categories=[Category.MLE]) for n in skill_names],
    )


def _mock(array):
    return LLMClient(responder=lambda system, user: json.dumps(array))


def test_tailor_skills_returns_groups():
    lib = _lib(["Python", "PyTorch", "SQL", "Excel"])
    client = _mock([
        {"label": "Programming", "skills": ["Python", "SQL"]},
        {"label": "Machine Learning", "skills": ["PyTorch"]},
    ])
    groups = tailor_skills(_jd(), lib, client=client)
    assert [g.label for g in groups] == ["Programming", "Machine Learning"]
    assert groups[1].skills == ["PyTorch"]


def test_tailor_skills_drops_empty_and_unlabeled():
    lib = _lib(["Python"])
    client = _mock([
        {"label": "", "skills": ["Python"]},      # no label -> dropped
        {"label": "Tools", "skills": []},          # no skills -> dropped
        {"label": "Programming", "skills": ["Python"]},
    ])
    groups = tailor_skills(_jd(), lib, client=client)
    assert len(groups) == 1 and groups[0].label == "Programming"


def test_tailor_skills_fallback_to_flat_when_empty():
    lib = _lib(["Python", "SQL"])
    groups = tailor_skills(_jd(), lib, client=_mock([]))
    assert len(groups) == 1
    assert groups[0].label == "Skills"
    assert groups[0].skills == ["Python", "SQL"]


def test_tailor_skills_no_inventory_returns_empty():
    groups = tailor_skills(_jd(), _lib([]), client=_mock([{"label": "X", "skills": ["Y"]}]))
    assert groups == []
