"""M3 tests: scoring + selection. Pure functions, no LLM needed."""

from __future__ import annotations

from app.materials_store import load_materials
from app.pipeline.scoring import score_bullet
from app.pipeline.step3_selection import select_experiences
from app.schemas import (
    Bullet,
    Category,
    Experience,
    JDProfile,
    MaterialsLibrary,
    PersonalInfo,
    Project,
    Skill,
)


def _jd(**kw) -> JDProfile:
    base = dict(
        job_title="MLE",
        company="Acme",
        primary_category="MLE",
        secondary_categories=[],
        key_skills=[],
        keywords_for_highlight=[],
    )
    base.update(kw)
    return JDProfile.model_validate(base)


# ---- scoring -------------------------------------------------------------

def test_score_counts_highlight_and_skill_hits():
    b = Bullet(id="b1", text="Built RAG pipeline in Python", skill_tags=["PyTorch", "RAG"])
    jd = _jd(keywords_for_highlight=["PyTorch", "RAG"], key_skills=["Python"])
    res = score_bullet(b, jd)
    # 2 highlight hits * 2.0 + 1 skill hit * 1.0 = 5.0
    assert res.score == 5.0
    assert set(res.matched_keywords) == {"PyTorch", "RAG", "Python"}


def test_score_word_boundary_no_false_match():
    # "ML" must not match inside "HTML"; "Spark" must not match "Sparkle".
    b = Bullet(id="b1", text="Wrote HTML and added sparkle effects", skill_tags=[])
    jd = _jd(keywords_for_highlight=["ML", "Spark"])
    assert score_bullet(b, jd).score == 0.0


def test_score_no_double_count_skill_already_highlight():
    b = Bullet(id="b1", text="Python work", skill_tags=["Python"])
    jd = _jd(keywords_for_highlight=["Python"], key_skills=["Python"])
    # Only counted once (as highlight), not again as skill.
    assert score_bullet(b, jd).score == 2.0


# ---- selection -----------------------------------------------------------

def _library() -> MaterialsLibrary:
    return MaterialsLibrary(
        personal_info=PersonalInfo(name="J", email="e", phone="p"),
        experiences=[
            Experience(
                id="exp_mle",
                title="MLE Intern",
                organization="A",
                categories=[Category.MLE, Category.AI],
                bullets=[
                    Bullet(id="m1", text="Trained PyTorch models", skill_tags=["PyTorch"], priority=2),
                    Bullet(id="m2", text="Wrote docs", skill_tags=["Writing"], priority=1),
                    Bullet(id="m3", text="Used Kubernetes", skill_tags=["Kubernetes"], priority=1),
                ],
            ),
            Experience(
                id="exp_de",
                title="DE Intern",
                organization="B",
                categories=[Category.DE],  # not in interest -> filtered out
                bullets=[Bullet(id="d1", text="Built Airflow ETL", skill_tags=["Airflow"])],
            ),
        ],
        projects=[
            Project(
                id="proj_ai",
                title="AI proj",
                categories=[Category.AI],
                bullets=[Bullet(id="p1", text="LLM agent with PyTorch", skill_tags=["PyTorch", "LLM"])],
            )
        ],
        skills=[
            Skill(name="PyTorch", categories=[Category.MLE]),
            Skill(name="Airflow", categories=[Category.DE]),
        ],
    )


def test_category_filter_excludes_non_matching():
    jd = _jd(primary_category="MLE", secondary_categories=["AI"], keywords_for_highlight=["PyTorch", "Kubernetes"])
    res = select_experiences(jd, _library())
    ids = {g.source_id for g in res.selected_experiences}
    assert "exp_mle" in ids
    assert "exp_de" not in ids  # DE category not of interest
    assert {g.source_id for g in res.selected_projects} == {"proj_ai"}


def test_bullets_ordered_by_score():
    jd = _jd(primary_category="MLE", secondary_categories=["AI"], keywords_for_highlight=["PyTorch", "Kubernetes"])
    res = select_experiences(jd, _library())
    mle = next(g for g in res.selected_experiences if g.source_id == "exp_mle")
    scores = [b.score for b in mle.selected_bullets]
    assert scores == sorted(scores, reverse=True)
    # The unrelated "Wrote docs" bullet (score 0) should rank last / be dropped first.
    assert mle.selected_bullets[0].source_bullet_id == "m1"


def test_target_bullet_count_trims_but_keeps_one_per_group():
    jd = _jd(primary_category="MLE", secondary_categories=["AI"], keywords_for_highlight=["PyTorch", "Kubernetes"])
    res = select_experiences(jd, _library(), target_bullet_count=2)
    total = sum(len(g.selected_bullets) for g in res.selected_experiences + res.selected_projects)
    assert total <= 2
    # Even after aggressive trimming, each surviving group keeps >=1 bullet.
    for g in res.selected_experiences + res.selected_projects:
        assert len(g.selected_bullets) >= 1


def test_skills_and_education_selection():
    jd = _jd(primary_category="MLE", secondary_categories=["AI"])
    res = select_experiences(jd, _library())
    assert "PyTorch" in res.selected_skills
    assert "Airflow" not in res.selected_skills  # DE-only skill


def test_runs_on_sample_library():
    jd = _jd(
        primary_category="MLE",
        secondary_categories=["AI", "DS"],
        key_skills=["Python", "PyTorch"],
        keywords_for_highlight=["PyTorch", "RAG", "Docker"],
    )
    res = select_experiences(jd, load_materials())
    assert res.selected_experiences  # sample data yields at least one match
    assert all(b.score >= 0 for g in res.selected_experiences for b in g.selected_bullets)
