"""Merge a freshly-parsed library into an existing one (append-from-new-resume).

Pure functions, no I/O — unit-testable in isolation. Strategy:
- Experiences match by (organization, title); on match, append only NEW bullets
  (deduped by normalized text). Otherwise add the experience.
- Projects match by title (same bullet-append behavior).
- Education matches by (school, degree); add if new.
- Skills match by name; on match, union their categories. Otherwise add.
After merging, all ids are renumbered to stay unique and tidy.
"""

from __future__ import annotations

from .schemas import Bullet, Category, MaterialsLibrary


def _norm(s: str) -> str:
    return (s or "").strip().lower()


def _append_new_bullets(existing_bullets: list[Bullet], incoming_bullets: list[Bullet]) -> None:
    seen = {_norm(b.text) for b in existing_bullets}
    for b in incoming_bullets:
        if _norm(b.text) not in seen:
            existing_bullets.append(b)
            seen.add(_norm(b.text))


def merge_libraries(base: MaterialsLibrary, incoming: MaterialsLibrary) -> MaterialsLibrary:
    result = base.model_copy(deep=True)

    # Experiences by (org, title).
    exp_index = {(_norm(e.organization), _norm(e.title)): e for e in result.experiences}
    for inc in incoming.experiences:
        key = (_norm(inc.organization), _norm(inc.title))
        if key in exp_index:
            _append_new_bullets(exp_index[key].bullets, inc.bullets)
        else:
            result.experiences.append(inc.model_copy(deep=True))
            exp_index[key] = result.experiences[-1]

    # Projects by title.
    proj_index = {_norm(p.title): p for p in result.projects}
    for inc in incoming.projects:
        key = _norm(inc.title)
        if key in proj_index:
            _append_new_bullets(proj_index[key].bullets, inc.bullets)
        else:
            result.projects.append(inc.model_copy(deep=True))
            proj_index[key] = result.projects[-1]

    # Education by (school, degree).
    edu_seen = {(_norm(e.school), _norm(e.degree)) for e in result.education}
    for inc in incoming.education:
        key = (_norm(inc.school), _norm(inc.degree))
        if key not in edu_seen:
            result.education.append(inc.model_copy(deep=True))
            edu_seen.add(key)

    # Skills by name; union categories on match.
    skill_index = {_norm(s.name): s for s in result.skills}
    for inc in incoming.skills:
        key = _norm(inc.name)
        if key in skill_index:
            existing = skill_index[key]
            merged = {*existing.categories, *inc.categories}
            existing.categories = sorted(merged, key=lambda c: c.value)
        else:
            result.skills.append(inc.model_copy(deep=True))
            skill_index[key] = result.skills[-1]

    _renumber_ids(result)
    return result


def _renumber_ids(lib: MaterialsLibrary) -> None:
    """Reassign stable, unique, increasing ids across the whole library."""
    for i, e in enumerate(lib.education, 1):
        e.id = f"edu_{i:03d}"

    bullet_n = 0
    for i, exp in enumerate(lib.experiences, 1):
        exp.id = f"exp_{i:03d}"
        for b in exp.bullets:
            bullet_n += 1
            b.id = f"bullet_{bullet_n:03d}"
    for i, proj in enumerate(lib.projects, 1):
        proj.id = f"proj_{i:03d}"
        for b in proj.bullets:
            bullet_n += 1
            b.id = f"bullet_{bullet_n:03d}"
