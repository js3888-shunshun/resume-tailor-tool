"""Step 7 tests: cover letter generation (mocked LLM) + rendering."""

from __future__ import annotations

import json

from app.llm import LLMClient
from app.pipeline.step7_cover_letter import _sanitize, generate_cover_letter
from app.render.cover_letter import render_cover_letter
from app.schemas import (
    Bullet,
    CoverLetterDocument,
    Experience,
    JDProfile,
    MaterialsLibrary,
    PersonalInfo,
    RenderContact,
    Skill,
)


def _lib() -> MaterialsLibrary:
    return MaterialsLibrary(
        personal_info=PersonalInfo(name="Joy Sun", email="j@x.com", phone="123",
                                   location="New York, NY"),
        experiences=[Experience(id="e1", title="ML Intern", organization="Acme",
                                bullets=[Bullet(id="b1", text="Built a RAG pipeline, cut latency 30%")])],
        skills=[Skill(name="Python"), Skill(name="PyTorch")],
    )


def _jd() -> JDProfile:
    return JDProfile(job_title="ML Engineer", company="Globex", primary_category="MLE",
                     key_skills=["Python", "RAG"], key_responsibilities=["Build ML systems"])


def test_sanitize_strips_ai_punctuation():
    out = _sanitize("I led the team — with strong results (and real impact).")
    assert "—" not in out and "(" not in out and ")" not in out
    assert "strong results" in out and "real impact" in out


def test_generate_uses_mock_and_sanitizes():
    reply = json.dumps({
        "salutation": "Dear Hiring Manager,",
        "paragraphs": [
            "I am applying for the ML Engineer role — I build RAG systems (in Python).",
            "At Acme I cut latency by 30 percent.",
        ],
        "closing": "Sincerely,",
    })
    client = LLMClient(responder=lambda s, u: reply)
    parts = generate_cover_letter(_jd(), _lib(), client=client)
    assert parts["salutation"] == "Dear Hiring Manager,"
    assert len(parts["paragraphs"]) == 2
    joined = " ".join(parts["paragraphs"])
    assert "—" not in joined and "(" not in joined and ")" not in joined


def test_background_includes_real_content():
    # The user prompt must carry the candidate's real org / skills (no fabrication).
    captured = {}

    def responder(system, user):
        captured["user"] = user
        return json.dumps({"salutation": "Dear Hiring Manager,", "paragraphs": ["x"], "closing": "Sincerely,"})

    generate_cover_letter(_jd(), _lib(), client=LLMClient(responder=responder))
    assert "Acme" in captured["user"]
    assert "Python" in captured["user"]
    assert "Globex" in captured["user"]  # target company


def test_render_cover_letter_escapes_and_balances():
    doc = CoverLetterDocument(
        contact=RenderContact(name="Joy & Co", email="j@x.com", location="NYC"),
        date="June 19, 2026", company="Globex 50%", job_title="ML Engineer",
        salutation="Dear Hiring Manager,",
        paragraphs=["I saved 30% and cut $1M in cost.", "Second paragraph."],
        closing="Sincerely,",
    )
    tex = render_cover_letter(doc)
    assert tex.count("{") == tex.count("}")
    assert r"Joy \& Co" in tex
    assert r"30\%" in tex and r"\$1M" in tex
    assert r"Globex 50\%" in tex
    assert "Dear Hiring Manager," in tex
