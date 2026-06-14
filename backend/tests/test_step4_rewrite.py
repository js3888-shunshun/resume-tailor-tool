"""M4 tests: bullet rewriting with an injected mock LLM responder."""

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


def _exp(bullets):
    return SelectedExperience(source_id="exp_001",
                              selected_bullets=[SelectedBullet(source_bullet_id=bid, original_text=txt) for bid, txt in bullets])


def _mock(array):
    text = json.dumps(array)
    return LLMClient(responder=lambda system, user: text)


def test_rewrite_fills_text_and_keywords():
    exp = _exp([("m1", "Built models in python"), ("m2", "Deployed services")])
    client = _mock([
        {"id": "b0", "rewritten_text": "Trained PyTorch models", "matched_keywords": ["PyTorch"]},
        {"id": "b1", "rewritten_text": "Deployed services on Kubernetes", "matched_keywords": ["Kubernetes"]},
    ])
    exps, _ = rewrite_selected(_jd(), [exp], [], client=client)
    bullets = exps[0].selected_bullets
    assert bullets[0].rewritten_text == "Trained PyTorch models"
    assert bullets[0].matched_keywords == ["PyTorch"]
    assert bullets[1].rewritten_text == "Deployed services on Kubernetes"


def test_rewrite_batches_experiences_and_projects_with_global_ids():
    exp = _exp([("m1", "a")])
    proj = SelectedExperience(source_id="proj_001",
                              selected_bullets=[SelectedBullet(source_bullet_id="p1", original_text="b")])
    # b0 = experience bullet, b1 = project bullet (global indexing across both lists)
    client = _mock([
        {"id": "b0", "rewritten_text": "A rewritten", "matched_keywords": []},
        {"id": "b1", "rewritten_text": "B rewritten", "matched_keywords": []},
    ])
    exps, projs = rewrite_selected(_jd(), [exp], [proj], client=client)
    assert exps[0].selected_bullets[0].rewritten_text == "A rewritten"
    assert projs[0].selected_bullets[0].rewritten_text == "B rewritten"


def test_missing_item_falls_back_to_original():
    exp = _exp([("m1", "original text"), ("m2", "second")])
    client = _mock([{"id": "b0", "rewritten_text": "only first", "matched_keywords": []}])
    exps, _ = rewrite_selected(_jd(), [exp], [], client=client)
    # b1 had no response -> keep original, nothing dropped.
    assert exps[0].selected_bullets[1].rewritten_text == "second"


def test_tolerates_dict_wrapped_array():
    exp = _exp([("m1", "a")])
    client = _mock({"bullets": [{"id": "b0", "rewritten_text": "wrapped ok", "matched_keywords": []}]})
    exps, _ = rewrite_selected(_jd(), [exp], [], client=client)
    assert exps[0].selected_bullets[0].rewritten_text == "wrapped ok"


def test_no_bullets_noop():
    exps, projs = rewrite_selected(_jd(), [], [], client=_mock([]))
    assert exps == [] and projs == []


def test_missing_key_raises():
    exp = _exp([("m1", "a")])
    with pytest.raises(LLMError):
        rewrite_selected(_jd(), [exp], [], client=LLMClient(api_key="", responder=None))
