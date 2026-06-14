"""Step 3: select the most relevant experiences/projects (pre-rewrite).

The unit of selection is the EXPERIENCE (or project), not the individual bullet.
We score each experience as a whole against the JD (category fit + keyword
breadth), then keep the top N experiences and top M projects. A selected
experience keeps ALL of its bullets — bullet-level trimming for one-page fit
happens later in the Step 6 compile loop, not here.

Pure functions, no LLM. Scoring is delegated to a swappable `ExperienceScorer`.
"""

from __future__ import annotations

import logging
from typing import List, Sequence

from ..schemas import (
    Education,
    Experience,
    JDProfile,
    MaterialsLibrary,
    Project,
    SelectedBullet,
    SelectedExperience,
    SelectionResult,
    Skill,
)
from .scoring import ExperienceScorer, score_experience

logger = logging.getLogger("resume_tailor.step3")

# How many sections of each kind to keep by default.
DEFAULT_TARGET_EXPERIENCES = 4
DEFAULT_TARGET_PROJECTS = 2


def _categories_of_interest(jd: JDProfile) -> set:
    return {jd.primary_category, *jd.secondary_categories}


def _select_top(
    items: Sequence[Experience | Project],
    jd: JDProfile,
    scorer: ExperienceScorer,
    target: int,
) -> List[SelectedExperience]:
    """Filter by category intersection, score each item whole, keep the top `target`."""
    cats = _categories_of_interest(jd)
    scored: List[tuple] = []
    for item in items:
        if not (set(item.categories) & cats):
            continue
        es = scorer(item, jd)
        scored.append((item, es))

    # Best experiences first; tiebreak by bullet count (richer experience first).
    scored.sort(key=lambda pair: (pair[1].score, len(pair[0].bullets)), reverse=True)

    selected: List[SelectedExperience] = []
    for item, es in scored[: max(0, target)]:
        selected.append(
            SelectedExperience(
                source_id=item.id,
                score=es.score,
                matched_keywords=es.matched_keywords,
                # Keep the whole experience: all bullets travel together.
                selected_bullets=[
                    SelectedBullet(
                        source_bullet_id=b.id,
                        original_text=b.text,
                        matched_keywords=es.bullet_matches.get(b.id, []),
                    )
                    for b in item.bullets
                ],
            )
        )
    return selected


def _select_skills(skills: Sequence[Skill], jd: JDProfile) -> List[str]:
    cats = _categories_of_interest(jd)
    return [s.name for s in skills if set(s.categories) & cats]


def _select_education(education: Sequence[Education]) -> List[str]:
    return [e.id for e in education]


def select_experiences(
    jd: JDProfile,
    library: MaterialsLibrary,
    *,
    target_experiences: int = DEFAULT_TARGET_EXPERIENCES,
    target_projects: int = DEFAULT_TARGET_PROJECTS,
    scorer: ExperienceScorer = score_experience,
) -> SelectionResult:
    """Run Step 3: pick whole experiences/projects by section-count targets."""
    exp_groups = _select_top(library.experiences, jd, scorer, target_experiences)
    proj_groups = _select_top(library.projects, jd, scorer, target_projects)

    result = SelectionResult(
        selected_education=_select_education(library.education),
        selected_experiences=exp_groups,
        selected_projects=proj_groups,
        selected_skills=_select_skills(library.skills, jd),
    )
    logger.info(
        "Selection: %d/%d experiences, %d/%d projects, %d skills",
        len(exp_groups),
        target_experiences,
        len(proj_groups),
        target_projects,
        len(result.selected_skills),
    )
    return result
