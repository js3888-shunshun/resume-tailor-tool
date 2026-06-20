"""Tests for the JD match score (mocked LLM)."""

from __future__ import annotations

import json

from app.llm import LLMClient
from app.pipeline.match_score import score_match
from app.schemas import (
    Bullet,
    Experience,
    JDProfile,
    MaterialsLibrary,
    PersonalInfo,
    Skill,
)


def _lib():
    return MaterialsLibrary(
        personal_info=PersonalInfo(name="J", email="j@x.com", phone="1"),
        experiences=[Experience(id="e1", title="ML Intern", organization="Acme",
                                domains=["finance"],
                                bullets=[Bullet(id="b1", text="Built models")])],
        skills=[Skill(name="Python")],
    )


def _jd():
    return JDProfile(job_title="MLE", company="Globex", primary_category="MLE",
                     key_skills=["Python"], key_responsibilities=["Build ML"])


def test_score_match_parses_and_clamps():
    reply = json.dumps({"score": 142, "summary": "strong", "strengths": ["a", ""], "gaps": ["b"]})
    out = score_match(_jd(), _lib(), client=LLMClient(responder=lambda s, u: reply))
    assert out["score"] == 100  # clamped to 0..100
    assert out["summary"] == "strong"
    assert out["strengths"] == ["a"]  # blanks dropped
    assert out["gaps"] == ["b"]


def test_score_match_handles_bad_score():
    reply = json.dumps({"score": "n/a", "strengths": [], "gaps": []})
    out = score_match(_jd(), _lib(), client=LLMClient(responder=lambda s, u: reply))
    assert out["score"] == 0


def test_background_includes_domain_and_skills():
    captured = {}

    def responder(s, u):
        captured["u"] = u
        return json.dumps({"score": 70, "strengths": [], "gaps": []})

    score_match(_jd(), _lib(), client=LLMClient(responder=responder))
    assert "finance" in captured["u"]   # domain tag surfaced
    assert "Python" in captured["u"]
    assert "Globex" in captured["u"]
