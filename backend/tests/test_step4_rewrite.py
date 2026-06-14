"""M4 tests: whole-experience rewriting with an injected mock LLM responder."""

from __future__ import annotations

import json

import pytest

from app.llm import LLMClient, LLMError
from app.pipeline.step4_rewrite import rewrite_selected
from app.schemas import JDProfile, SelectedBullet, SelectedExperience


def _jd():
    return JDProfile.model_validate({
        "job_title": "MLE", "company": "Acme", "primary_category": "MLE",
        "keywords_for_highlight": ["PyTorch", "Kubernetes"], "key_skills": ["Python"],
    })


def _exp(source_id, bullets):
    return SelectedExperience(source_id=source_id,
                              selected_bullets=[SelectedBullet(source_bullet_id=bid, original_text=txt) for bid, txt in bullets])


def _mock(array):
    return LLMClient(responder=lambda system, user: json.dumps(array))


def test_whole_experience_rewrite_can_change_bullet_count():
    exp = _exp("exp_001", [("m1", "did ml stuff"), ("m2", "minor filler task"), ("m3", "another minor thing")])
    # Model condenses 3 bullets -> 2 tailored bullets.
    client = _mock([{"id": "e0", "bullets": [
        {"text": "Built PyTorch models in production", "matched_keywords": ["PyTorch"]},
        {"text": "Deployed services on Kubernetes", "matched_keywords": ["Kubernetes"]},
    ]}])
    exps, _ = rewrite_selected(_jd(), [exp], [], client=client)
    rb = exps[0].rewritten_bullets
    assert len(rb) == 2  # fewer than the 3 originals
    assert rb[0].rewritten_text == "Built PyTorch models in production"
    assert rb[0].matched_keywords == ["PyTorch"]
    # Originals preserved for before -> after display.
    assert len(exps[0].selected_bullets) == 3


def test_batches_experiences_and_projects_with_ids():
    exp = _exp("exp_001", [("m1", "a")])
    proj = _exp("proj_001", [("p1", "b")])
    client = _mock([
        {"id": "e0", "bullets": [{"text": "Exp rewritten", "matched_keywords": []}]},
        {"id": "e1", "bullets": [{"text": "Proj rewritten", "matched_keywords": []}]},
    ])
    exps, projs = rewrite_selected(_jd(), [exp], [proj], client=client)
    assert exps[0].rewritten_bullets[0].rewritten_text == "Exp rewritten"
    assert projs[0].rewritten_bullets[0].rewritten_text == "Proj rewritten"


def test_missing_experience_falls_back_to_originals():
    exp = _exp("exp_001", [("m1", "keep me"), ("m2", "and me")])
    client = _mock([])  # model returned nothing for e0
    exps, _ = rewrite_selected(_jd(), [exp], [], client=client)
    texts = [b.rewritten_text for b in exps[0].rewritten_bullets]
    assert texts == ["keep me", "and me"]  # nothing dropped


def test_uses_context_titles(monkeypatch):
    exp = _exp("exp_001", [("m1", "a")])
    captured = {}
    def responder(system, user):
        captured["user"] = user
        return json.dumps([{"id": "e0", "bullets": [{"text": "x", "matched_keywords": []}]}])
    client = LLMClient(responder=responder)
    rewrite_selected(_jd(), [exp], [], context={"exp_001": {"title": "ML Engineer Intern", "organization": "BigCo"}}, client=client)
    assert "ML Engineer Intern" in captured["user"]


def test_tolerates_dict_wrapped_array():
    exp = _exp("exp_001", [("m1", "a")])
    client = _mock({"experiences": [{"id": "e0", "bullets": [{"text": "wrapped ok", "matched_keywords": []}]}]})
    exps, _ = rewrite_selected(_jd(), [exp], [], client=client)
    assert exps[0].rewritten_bullets[0].rewritten_text == "wrapped ok"


def test_no_bullets_noop():
    exps, projs = rewrite_selected(_jd(), [], [], client=_mock([]))
    assert exps == [] and projs == []


def test_missing_key_raises():
    exp = _exp("exp_001", [("m1", "a")])
    with pytest.raises(LLMError):
        rewrite_selected(_jd(), [exp], [], client=LLMClient(api_key="", responder=None))
