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


def _to_selected(item: Experience | Project, es) -> SelectedExperience:
    return SelectedExperience(
        source_id=item.id,
        score=es.score,
        matched_keywords=es.matched_keywords,
        matched_categories=es.matched_categories,
        category_score=es.category_score,
        keyword_score=es.keyword_score,
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


def _rank(
    items: Sequence[Experience | Project],
    jd: JDProfile,
    scorer: ExperienceScorer,
) -> List[SelectedExperience]:
    """Filter by category intersection and rank every candidate, best first."""
    cats = _categories_of_interest(jd)
    scored = [(item, scorer(item, jd)) for item in items if set(item.categories) & cats]
    # Best first; tiebreak by bullet count (richer experience first).
    scored.sort(key=lambda pair: (pair[1].score, len(pair[0].bullets)), reverse=True)
    return [_to_selected(item, es) for item, es in scored]


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
    ranked_exp = _rank(library.experiences, jd, scorer)
    ranked_proj = _rank(library.projects, jd, scorer)

    result = SelectionResult(
        selected_education=_select_education(library.education),
        selected_experiences=ranked_exp[: max(0, target_experiences)],
        selected_projects=ranked_proj[: max(0, target_projects)],
        selected_skills=_select_skills(library.skills, jd),
        ranked_experiences=ranked_exp,
        ranked_projects=ranked_proj,
    )
    logger.info(
        "Selection: %d/%d experiences (of %d candidates), %d/%d projects, %d skills",
        len(result.selected_experiences),
        target_experiences,
        len(ranked_exp),
        len(result.selected_projects),
        target_projects,
        len(result.selected_skills),
    )
    return result
