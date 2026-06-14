"""Step 3: select the most relevant experiences/projects/skills (pre-rewrite).

Pure functions, no LLM. Given a JD profile + material library, produce a
`SelectionResult` describing which bullets were chosen and their scores.
The scoring is delegated to a swappable `Scorer` (see `scoring.py`).
"""

from __future__ import annotations

import logging
from typing import List, Sequence, Tuple

from ..schemas import (
    Category,
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
from .scoring import Scorer, score_bullet

logger = logging.getLogger("resume_tailor.step3")

# Defaults; the bullet target can be overridden per request.
DEFAULT_TARGET_BULLET_COUNT = 12
DEFAULT_MAX_BULLETS_PER_ITEM = 4
DEFAULT_MIN_BULLETS_PER_ITEM = 1


def _categories_of_interest(jd: JDProfile) -> set[Category]:
    return {jd.primary_category, *jd.secondary_categories}


def _select_from_items(
    items: Sequence[Experience | Project],
    jd: JDProfile,
    scorer: Scorer,
    max_per_item: int,
    min_per_item: int,
) -> List[SelectedExperience]:
    """Filter by category intersection, score bullets, keep the best per item."""
    cats = _categories_of_interest(jd)
    selected: List[SelectedExperience] = []

    for item in items:
        if not (set(item.categories) & cats):
            continue

        scored = [(b, scorer(b, jd)) for b in item.bullets]
        # Best first: higher score, then higher priority as tiebreak.
        scored.sort(key=lambda pair: (pair[1].score, pair[0].priority), reverse=True)

        positive = [pair for pair in scored if pair[1].score > 0]
        chosen = positive[:max_per_item]
        if not chosen:
            # Category matched but no keyword hit: still keep the item with its
            # top-priority bullet(s) so a relevant role isn't dropped entirely.
            chosen = scored[:min_per_item]

        selected.append(
            SelectedExperience(
                source_id=item.id,
                selected_bullets=[
                    SelectedBullet(
                        source_bullet_id=b.id,
                        original_text=b.text,
                        score=bs.score,
                        matched_keywords=bs.matched_keywords,
                    )
                    for b, bs in chosen
                ],
            )
        )
    return selected


def _total_bullets(groups: Sequence[SelectedExperience]) -> int:
    return sum(len(g.selected_bullets) for g in groups)


def _trim_to_target(groups: Sequence[SelectedExperience], target: int) -> None:
    """Drop the globally lowest-scoring bullets until total <= target.

    Never empties a group: a group keeps at least one bullet so the
    experience/project still appears on the resume. Mutates in place.
    """
    while _total_bullets(groups) > target:
        removable: List[Tuple[SelectedExperience, SelectedBullet]] = [
            (g, b)
            for g in groups
            if len(g.selected_bullets) > 1
            for b in g.selected_bullets
        ]
        if not removable:
            break  # every group is down to its last bullet
        group, bullet = min(removable, key=lambda pair: pair[1].score)
        group.selected_bullets.remove(bullet)


def _select_skills(skills: Sequence[Skill], jd: JDProfile) -> List[str]:
    cats = _categories_of_interest(jd)
    return [s.name for s in skills if set(s.categories) & cats]


def _select_education(education: Sequence[Education]) -> List[str]:
    # Education has no categories; keep all (it's always shown on a resume).
    return [e.id for e in education]


def select_experiences(
    jd: JDProfile,
    library: MaterialsLibrary,
    *,
    target_bullet_count: int = DEFAULT_TARGET_BULLET_COUNT,
    max_bullets_per_item: int = DEFAULT_MAX_BULLETS_PER_ITEM,
    min_bullets_per_item: int = DEFAULT_MIN_BULLETS_PER_ITEM,
    scorer: Scorer = score_bullet,
) -> SelectionResult:
    """Run Step 3 and return a pre-rewrite `SelectionResult`."""
    exp_groups = _select_from_items(
        library.experiences, jd, scorer, max_bullets_per_item, min_bullets_per_item
    )
    proj_groups = _select_from_items(
        library.projects, jd, scorer, max_bullets_per_item, min_bullets_per_item
    )

    # Trim experiences and projects together against one global budget,
    # experiences first (resume convention: experience outweighs projects).
    _trim_to_target([*exp_groups, *proj_groups], target_bullet_count)

    # Drop any groups that ended up empty (shouldn't happen, but be safe).
    exp_groups = [g for g in exp_groups if g.selected_bullets]
    proj_groups = [g for g in proj_groups if g.selected_bullets]

    result = SelectionResult(
        selected_education=_select_education(library.education),
        selected_experiences=exp_groups,
        selected_projects=proj_groups,
        selected_skills=_select_skills(library.skills, jd),
    )
    logger.info(
        "Selection: %d experiences / %d projects / %d bullets / %d skills",
        len(exp_groups),
        len(proj_groups),
        _total_bullets([*exp_groups, *proj_groups]),
        len(result.selected_skills),
    )
    return result
