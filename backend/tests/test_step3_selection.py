"""M3 tests: scoring + experience-level selection. Pure functions, no LLM."""

from __future__ import annotations

from app.materials_store import load_materials
from app.pipeline.scoring import score_bullet, score_experience
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
    base = dict(job_title="MLE", company="Acme", primary_category="MLE",
                secondary_categories=[], key_skills=[], keywords_for_highlight=[])
    base.update(kw)
    return JDProfile.model_validate(base)


# ---- bullet scoring (ingredient) ----------------------------------------

def test_score_bullet_counts_hits():
    b = Bullet(id="b1", text="Built RAG pipeline in Python", skill_tags=["PyTorch", "RAG"])
    jd = _jd(keywords_for_highlight=["PyTorch", "RAG"], key_skills=["Python"])
    res = score_bullet(b, jd)
    assert res.score == 5.0
    assert set(res.matched_keywords) == {"PyTorch", "RAG", "Python"}


def test_score_bullet_word_boundary():
    b = Bullet(id="b1", text="Wrote HTML and added sparkle", skill_tags=[])
    jd = _jd(keywords_for_highlight=["ML", "Spark"])
    assert score_bullet(b, jd).score == 0.0


# ---- experience scoring --------------------------------------------------

def test_experience_score_includes_category_and_keywords():
    exp = Experience(id="e1", title="MLE", organization="A",
                     categories=[Category.MLE, Category.AI],
                     bullets=[Bullet(id="b1", text="PyTorch models", skill_tags=["PyTorch"]),
                              Bullet(id="b2", text="Used Docker", skill_tags=["Docker"])])
    jd = _jd(primary_category="MLE", secondary_categories=["AI"],
             keywords_for_highlight=["PyTorch", "Docker"])
    es = score_experience(exp, jd)
    # primary(3) + 1 secondary(1) + 2 distinct highlight kw * 2 = 3+1+4 = 8
    assert es.score == 8.0
    assert set(es.matched_keywords) == {"PyTorch", "Docker"}
    assert es.bullet_matches["b1"] == ["PyTorch"]


def test_experience_keywords_are_distinct_across_bullets():
    exp = Experience(id="e1", title="X", organization="A", categories=[Category.MLE],
                     bullets=[Bullet(id="b1", text="PyTorch", skill_tags=["PyTorch"]),
                              Bullet(id="b2", text="more PyTorch", skill_tags=["PyTorch"])])
    jd = _jd(primary_category="MLE", keywords_for_highlight=["PyTorch"])
    es = score_experience(exp, jd)
    # primary(3) + distinct PyTorch once *2 = 5 (not counted twice)
    assert es.score == 5.0
    assert es.matched_keywords == ["PyTorch"]


# ---- selection -----------------------------------------------------------

def _library() -> MaterialsLibrary:
    return MaterialsLibrary(
        personal_info=PersonalInfo(name="J", email="e", phone="p"),
        experiences=[
            Experience(id="exp_strong", title="MLE", organization="A",
                       categories=[Category.MLE, Category.AI],
                       bullets=[Bullet(id="s1", text="PyTorch RAG", skill_tags=["PyTorch", "RAG"]),
                                Bullet(id="s2", text="Kubernetes", skill_tags=["Kubernetes"])]),
            Experience(id="exp_weak", title="MLE2", organization="B",
                       categories=[Category.MLE],
                       bullets=[Bullet(id="w1", text="wrote docs", skill_tags=["Writing"])]),
            Experience(id="exp_off", title="DE", organization="C",
                       categories=[Category.DE],  # not of interest -> excluded
                       bullets=[Bullet(id="o1", text="Airflow", skill_tags=["Airflow"])]),
        ],
        projects=[
            Project(id="proj_a", title="P1", categories=[Category.AI],
                    bullets=[Bullet(id="p1", text="LLM agent PyTorch", skill_tags=["PyTorch", "LLM"])]),
            Project(id="proj_b", title="P2", categories=[Category.AI],
                    bullets=[Bullet(id="p2", text="static site", skill_tags=["HTML"])]),
        ],
        skills=[Skill(name="PyTorch", categories=[Category.MLE]),
                Skill(name="Airflow", categories=[Category.DE])],
    )


def _jd_full():
    return _jd(primary_category="MLE", secondary_categories=["AI"],
               keywords_for_highlight=["PyTorch", "RAG", "Kubernetes", "LLM"])


def test_whole_experiences_keep_all_bullets():
    res = select_experiences(_jd_full(), _library(), target_experiences=2, target_projects=2)
    strong = next(g for g in res.selected_experiences if g.source_id == "exp_strong")
    # The whole experience travels together — both bullets present, not split.
    assert {b.source_bullet_id for b in strong.selected_bullets} == {"s1", "s2"}


def test_target_counts_limit_sections():
    res = select_experiences(_jd_full(), _library(), target_experiences=1, target_projects=1)
    assert len(res.selected_experiences) == 1
    assert len(res.selected_projects) == 1
    # The single experience kept is the strongest one.
    assert res.selected_experiences[0].source_id == "exp_strong"
    assert res.selected_projects[0].source_id == "proj_a"


def test_category_filter_excludes_off_topic():
    res = select_experiences(_jd_full(), _library(), target_experiences=5)
    ids = {g.source_id for g in res.selected_experiences}
    assert "exp_off" not in ids  # DE-only experience excluded
    assert {"exp_strong", "exp_weak"} <= ids


def test_experiences_ranked_by_score():
    res = select_experiences(_jd_full(), _library(), target_experiences=5)
    scores = [g.score for g in res.selected_experiences]
    assert scores == sorted(scores, reverse=True)
    assert res.selected_experiences[0].source_id == "exp_strong"


def test_skills_filtered_by_category():
    res = select_experiences(_jd_full(), _library())
    assert "PyTorch" in res.selected_skills
    assert "Airflow" not in res.selected_skills


def test_score_breakdown_and_categories_exposed():
    res = select_experiences(_jd_full(), _library(), target_experiences=5)
    strong = next(g for g in res.selected_experiences if g.source_id == "exp_strong")
    # category_score + keyword_score == total score (transparent breakdown).
    assert strong.category_score + strong.keyword_score == strong.score
    assert "MLE (primary)" in strong.matched_categories
    assert "AI" in strong.matched_categories


def test_category_only_match_has_no_keywords():
    # exp_weak matches MLE category but its bullet ("wrote docs") hits no JD keyword.
    res = select_experiences(_jd_full(), _library(), target_experiences=5)
    weak = next(g for g in res.selected_experiences if g.source_id == "exp_weak")
    assert weak.matched_keywords == []          # explains "no tags below"
    assert weak.matched_categories == ["MLE (primary)"]
    assert weak.keyword_score == 0.0
    assert weak.score == weak.category_score     # selected purely on category fit


def test_ranked_includes_all_candidates_for_manual_swap():
    # target keeps 1, but ranked exposes all category-matching candidates so the
    # UI can let the user add/replace.
    res = select_experiences(_jd_full(), _library(), target_experiences=1)
    assert len(res.selected_experiences) == 1
    ranked_ids = {g.source_id for g in res.ranked_experiences}
    assert {"exp_strong", "exp_weak"} <= ranked_ids
    assert "exp_off" not in ranked_ids  # off-category still excluded entirely


def test_runs_on_sample_library():
    jd = _jd(primary_category="MLE", secondary_categories=["AI", "DS"],
             key_skills=["Python", "PyTorch"], keywords_for_highlight=["PyTorch", "RAG", "Docker"])
    res = select_experiences(jd, load_materials(), target_experiences=3, target_projects=2)
    assert res.selected_experiences
    assert all(g.score > 0 for g in res.selected_experiences)
