"""Tests for the application-question answer step (mocked LLM)."""

from __future__ import annotations

from app.llm import LLMClient
from app.pipeline.answer_question import _sanitize, answer_question
from app.schemas import Bullet, Experience, MaterialsLibrary, PersonalInfo, Skill


def _lib():
    return MaterialsLibrary(
        personal_info=PersonalInfo(name="J", email="j@x.com", phone="1"),
        experiences=[Experience(id="e1", title="ML Intern", organization="ByteDance",
                                bullets=[Bullet(id="b1", text="Built RAG in Python")])],
        skills=[Skill(name="Python")],
    )


def test_sanitize_drops_dashes():
    assert "—" not in _sanitize("I led a team — and shipped it")


def test_answer_uses_background_and_jd():
    captured = {}

    def responder(system, user):
        captured["u"] = user
        return "I built a RAG system at ByteDance using Python."

    out = answer_question("Why are you a fit?", _lib(),
                          jd_text="ML Engineer needing Python and RAG.",
                          client=LLMClient(responder=responder))
    assert "ByteDance" in captured["u"]            # background in prompt
    assert "RAG" in captured["u"]                  # JD context in prompt
    assert "Why are you a fit?" in captured["u"]   # the question
    assert "ByteDance" in out


def test_answer_returns_sanitized_text():
    out = answer_question("Q?", _lib(),
                          client=LLMClient(responder=lambda s, u: "great answer — really"))
    assert "—" not in out and out.startswith("great answer")
