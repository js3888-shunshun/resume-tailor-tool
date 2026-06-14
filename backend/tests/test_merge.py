"""Tests for merging a newly-parsed resume into an existing library."""

from __future__ import annotations

from app.materials_merge import merge_libraries
from app.schemas import (
    Bullet,
    Category,
    Education,
    Experience,
    MaterialsLibrary,
    PersonalInfo,
    Project,
    Skill,
)


def _lib(experiences=None, projects=None, skills=None, education=None) -> MaterialsLibrary:
    return MaterialsLibrary(
        personal_info=PersonalInfo(name="J", email="e", phone="p"),
        experiences=experiences or [],
        projects=projects or [],
        skills=skills or [],
        education=education or [],
    )


def test_append_new_bullets_to_matching_experience():
    base = _lib(experiences=[
        Experience(id="exp_001", title="MLE Intern", organization="Acme",
                   categories=[Category.MLE],
                   bullets=[Bullet(id="bullet_001", text="Trained models")])
    ])
    incoming = _lib(experiences=[
        Experience(id="x", title="mle intern", organization="ACME",  # case-insensitive match
                   categories=[Category.MLE],
                   bullets=[
                       Bullet(id="y", text="Trained models"),       # duplicate -> skipped
                       Bullet(id="z", text="Deployed to Kubernetes"),  # new -> added
                   ])
    ])
    merged = merge_libraries(base, incoming)
    assert len(merged.experiences) == 1
    texts = [b.text for b in merged.experiences[0].bullets]
    assert texts == ["Trained models", "Deployed to Kubernetes"]


def test_new_experience_added_separately():
    base = _lib(experiences=[
        Experience(id="exp_001", title="MLE", organization="Acme", categories=[Category.MLE],
                   bullets=[Bullet(id="bullet_001", text="a")])
    ])
    incoming = _lib(experiences=[
        Experience(id="x", title="Data Eng", organization="Beta", categories=[Category.DE],
                   bullets=[Bullet(id="y", text="b")])
    ])
    merged = merge_libraries(base, incoming)
    assert {e.title for e in merged.experiences} == {"MLE", "Data Eng"}


def test_skills_union_categories():
    base = _lib(skills=[Skill(name="Python", categories=[Category.SDE])])
    incoming = _lib(skills=[
        Skill(name="python", categories=[Category.MLE]),  # same name -> union cats
        Skill(name="SQL", categories=[Category.DE]),       # new
    ])
    merged = merge_libraries(base, incoming)
    names = {s.name for s in merged.skills}
    assert names == {"Python", "SQL"}
    py = next(s for s in merged.skills if s.name.lower() == "python")
    assert set(py.categories) == {Category.SDE, Category.MLE}


def test_education_dedup():
    edu = Education(id="edu_001", school="MIT", degree="BS", major="CS",
                    start_date="", end_date="")
    base = _lib(education=[edu])
    incoming = _lib(education=[
        Education(id="x", school="mit", degree="bs", major="CS", start_date="", end_date=""),  # dup
        Education(id="y", school="Stanford", degree="MS", major="CS", start_date="", end_date=""),
    ])
    merged = merge_libraries(base, incoming)
    assert {e.school for e in merged.education} == {"MIT", "Stanford"}


def test_ids_renumbered_and_unique():
    base = _lib(experiences=[
        Experience(id="exp_001", title="A", organization="X", categories=[Category.SDE],
                   bullets=[Bullet(id="bullet_001", text="a1")])
    ])
    incoming = _lib(
        experiences=[Experience(id="zz", title="B", organization="Y", categories=[Category.SDE],
                                bullets=[Bullet(id="qq", text="b1"), Bullet(id="rr", text="b2")])],
        projects=[Project(id="pp", title="P", categories=[Category.AI],
                          bullets=[Bullet(id="bb", text="p1")])],
    )
    merged = merge_libraries(base, incoming)
    exp_ids = [e.id for e in merged.experiences]
    assert exp_ids == ["exp_001", "exp_002"]
    bullet_ids = [b.id for e in merged.experiences for b in e.bullets] + \
                 [b.id for p in merged.projects for b in p.bullets]
    assert bullet_ids == ["bullet_001", "bullet_002", "bullet_003", "bullet_004"]
    assert len(bullet_ids) == len(set(bullet_ids))


def test_base_not_mutated():
    base = _lib(experiences=[
        Experience(id="exp_001", title="A", organization="X", categories=[Category.SDE],
                   bullets=[Bullet(id="bullet_001", text="a1")])
    ])
    incoming = _lib(experiences=[
        Experience(id="x", title="A", organization="X", categories=[Category.SDE],
                   bullets=[Bullet(id="y", text="a2")])
    ])
    merge_libraries(base, incoming)
    # Original base object must be untouched.
    assert len(base.experiences[0].bullets) == 1
