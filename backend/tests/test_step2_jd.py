"""M2 tests: JD analysis logic + endpoint, using an injected mock responder."""

from __future__ import annotations

import json

import pytest

from app.llm import LLMClient, LLMError
from app.pipeline.step2_jd_analysis import analyze_jd
from app.schemas import Category, JDProfile

VALID_JSON = {
    "job_title": "Machine Learning Engineer",
    "company": "Acme AI",
    "primary_category": "MLE",
    "secondary_categories": ["AI", "DS"],
    "key_skills": ["Python", "PyTorch", "Kubernetes"],
    "key_responsibilities": ["Train and deploy ML models"],
    "keywords_for_highlight": ["PyTorch", "RAG", "Kubernetes"],
    "tone_hints": "startup/casual",
}


def _mock_client(payload) -> LLMClient:
    text = payload if isinstance(payload, str) else json.dumps(payload)
    return LLMClient(responder=lambda system, user: text)


def test_analyze_jd_happy_path():
    profile = analyze_jd("We need an MLE...", client=_mock_client(VALID_JSON))
    assert isinstance(profile, JDProfile)
    assert profile.primary_category == Category.MLE
    assert Category.AI in profile.secondary_categories
    assert "PyTorch" in profile.keywords_for_highlight


def test_analyze_jd_tolerates_code_fences():
    fenced = "```json\n" + json.dumps(VALID_JSON) + "\n```"
    profile = analyze_jd("jd", client=_mock_client(fenced))
    assert profile.company == "Acme AI"


def test_analyze_jd_rejects_bad_category():
    bad = {**VALID_JSON, "primary_category": "WIZARD"}
    with pytest.raises(Exception):
        analyze_jd("jd", client=_mock_client(bad))


def test_analyze_jd_empty_input():
    with pytest.raises(ValueError):
        analyze_jd("   ", client=_mock_client(VALID_JSON))


def test_missing_key_raises_llmerror():
    # No responder, no api key -> should surface a clear LLMError.
    client = LLMClient(api_key="", responder=None)
    with pytest.raises(LLMError):
        analyze_jd("jd", client=client)


def test_invalid_json_retries_then_fails():
    client = LLMClient(responder=lambda s, u: "not json at all", max_retries=1)
    with pytest.raises(LLMError):
        analyze_jd("jd", client=client)
