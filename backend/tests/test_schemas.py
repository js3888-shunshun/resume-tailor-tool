"""M1 acceptance tests: schema validation + sample data loads."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.config import get_settings
from app.materials_store import validate_materials_file
from app.schemas import Category, JDProfile, MaterialsLibrary, SelectionResult

SAMPLE = get_settings().sample_materials_path


def test_sample_materials_validates():
    lib = validate_materials_file(SAMPLE)
    assert isinstance(lib, MaterialsLibrary)
    assert lib.personal_info.name
    assert len(lib.experiences) >= 1
    # Every experience category must be a valid enum member.
    for exp in lib.experiences:
        for cat in exp.categories:
            assert isinstance(cat, Category)


def test_bullet_priority_and_optional_metrics():
    lib = validate_materials_file(SAMPLE)
    bullets = [b for e in lib.experiences for b in e.bullets]
    assert any(b.impact_metrics is not None for b in bullets)
    assert all(isinstance(b.priority, int) for b in bullets)


def test_jdprofile_rejects_bad_category():
    with pytest.raises(Exception):
        JDProfile.model_validate(
            {
                "job_title": "X",
                "company": "Y",
                "primary_category": "NOT_A_CATEGORY",
            }
        )


def test_jdprofile_minimal_valid():
    p = JDProfile.model_validate(
        {"job_title": "MLE", "company": "Acme", "primary_category": "MLE"}
    )
    assert p.primary_category == Category.MLE
    assert p.secondary_categories == []


def test_selection_result_empty_ok():
    s = SelectionResult()
    assert s.selected_experiences == []
