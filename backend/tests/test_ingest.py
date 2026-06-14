"""M3.5 tests: resume decompose + text extraction + save/load roundtrip."""

from __future__ import annotations

import json

import pytest

from app.llm import LLMClient, LLMError
from app.materials_store import load_materials, save_materials
from app.pipeline.ingest import decompose_resume
from app.schemas import MaterialsLibrary
from app.text_extract import extract_text

LIB_JSON = {
    "personal_info": {"name": "Sam Lee", "email": "sam@x.com", "phone": "123", "links": []},
    "education": [
        {"id": "edu_001", "school": "MIT", "degree": "BS", "major": "CS",
         "start_date": "2019", "end_date": "2023", "details": []}
    ],
    "experiences": [
        {"id": "exp_001", "title": "SWE Intern", "organization": "Foo", "location": "NYC",
         "start_date": "2022", "end_date": "2022", "categories": ["SDE", "MLE"],
         "bullets": [
             {"id": "bullet_001", "text": "Built API in Python", "skill_tags": ["Python"],
              "impact_metrics": None, "priority": 2}
         ]}
    ],
    "projects": [],
    "skills": [{"name": "Python", "categories": ["SDE"], "proficiency": "advanced"}],
}


def _mock_client(payload) -> LLMClient:
    text = payload if isinstance(payload, str) else json.dumps(payload)
    return LLMClient(responder=lambda system, user: text)


def test_decompose_resume_happy_path():
    lib = decompose_resume("Sam Lee\nSWE Intern at Foo...", client=_mock_client(LIB_JSON))
    assert isinstance(lib, MaterialsLibrary)
    assert lib.personal_info.name == "Sam Lee"
    assert lib.experiences[0].bullets[0].skill_tags == ["Python"]


def test_decompose_resume_empty_input():
    with pytest.raises(ValueError):
        decompose_resume("   ", client=_mock_client(LIB_JSON))


def test_decompose_resume_invalid_schema_raises():
    bad = {"personal_info": {"name": "x"}}  # missing required email/phone
    with pytest.raises(Exception):
        decompose_resume("resume", client=_mock_client(bad))


def test_decompose_missing_key_raises():
    with pytest.raises(LLMError):
        decompose_resume("resume", client=LLMClient(api_key="", responder=None))


def test_extract_text_plain():
    assert "hello" in extract_text("resume.txt", b"hello world")
    assert "\\section" in extract_text("resume.tex", b"\\section{Experience}")


def test_save_and_load_roundtrip(tmp_path):
    lib = MaterialsLibrary.model_validate(LIB_JSON)
    target = tmp_path / "materials.json"
    save_materials(lib, path=target)
    assert target.exists()
    reloaded = load_materials(path=target)
    assert reloaded.personal_info.name == "Sam Lee"
    assert reloaded.experiences[0].id == "exp_001"
