"""Tests for the JD match score (mocked LLM)."""

from __future__ import annotations

import json

from app.llm import LLMClient
from app.pipeline.match_score import score_match
from app.schemas import (
    Bullet,
    Experience,
    MaterialsLibrary,
    PersonalInfo,
    Skill,
)

JD = "Machine Learning Engineer at Globex. Build ML systems in Python."


def _lib():
    return MaterialsLibrary(
        personal_info=PersonalInfo(name="J", email="j@x.com", phone="1"),
        experiences=[Experience(id="e1", title="ML Intern", organization="Acme",
                                domains=["finance"],
                                bullets=[Bullet(id="b1", text="Built models")])],
        skills=[Skill(name="Python")],
    )


def test_score_match_parses_and_clamps():
    reply = json.dumps({"score": 142, "summary": "strong", "strengths": ["a", ""], "gaps": ["b"]})
    out = score_match(JD, _lib(), client=LLMClient(responder=lambda s, u: reply))
    assert out["score"] == 100  # clamped to 0..100
    assert out["summary"] == "strong"
    assert out["strengths"] == ["a"]  # blanks dropped
    assert out["gaps"] == ["b"]


def test_score_match_handles_bad_score():
    reply = json.dumps({"score": "n/a", "strengths": [], "gaps": []})
    out = score_match(JD, _lib(), client=LLMClient(responder=lambda s, u: reply))
    assert out["score"] == 0


def test_prompt_includes_jd_and_background():
    captured = {}

    def responder(s, u):
        captured["u"] = u
        return json.dumps({"score": 70, "strengths": [], "gaps": []})

    score_match(JD, _lib(), client=LLMClient(responder=responder))
    assert "Globex" in captured["u"]    # raw JD text passed through
    assert "finance" in captured["u"]   # domain tag surfaced
    assert "Python" in captured["u"]
