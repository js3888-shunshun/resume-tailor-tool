"""Tunable spacing for the resume template (Step 6 one-page auto-fit).

The template's vertical spacing is parameterised so the fit loop can tighten the
layout to cram content onto one page, or loosen it to spread sparse content
evenly down to the page bottom — mimicking how a person nudges spacing to land a
resume on exactly one page. No content is changed; only typography.

A single `scale` in [0, 1] interpolates every knob between TIGHT (0) and LOOSE
(1). `DEFAULT` mirrors the previously hard-coded spacing and is used whenever the
fit loop isn't run (e.g. no LaTeX engine).
"""

from __future__ import annotations

from dataclasses import dataclass, fields


@dataclass(frozen=True)
class Layout:
    line_spread: float       # unitless, \linespread
    parskip: float           # pt, space between entries/paragraphs
    item_topsep: float       # pt, space above a bullet list
    item_itemsep: float      # pt, space between bullets
    section_before: float    # pt, space above a section heading
    section_after: float     # pt, space below a section heading

    def as_template(self) -> dict[str, str]:
        """Render to LaTeX-ready strings (pt units, fixed line_spread)."""
        return {
            "line_spread": f"{self.line_spread:.3f}",
            "parskip": f"{self.parskip:.2f}pt",
            "item_topsep": f"{self.item_topsep:.2f}pt",
            "item_itemsep": f"{self.item_itemsep:.2f}pt",
            "section_before": f"{self.section_before:.2f}pt",
            "section_after": f"{self.section_after:.2f}pt",
        }


# Mirrors the spacing the template used before M6 (so non-fit renders look same).
DEFAULT = Layout(1.0, 0.0, 1.0, 0.0, 4.0, 2.0)

# Search bounds. TIGHT = max content on one page; LOOSE = fill a sparse page.
TIGHT = Layout(1.00, 1.0, 0.0, 0.0, 3.0, 1.0)
LOOSE = Layout(1.32, 8.0, 5.0, 4.0, 14.0, 7.0)


def layout_for(scale: float) -> Layout:
    """Interpolate every knob between TIGHT (scale=0) and LOOSE (scale=1)."""
    s = max(0.0, min(1.0, scale))
    vals = {
        f.name: getattr(TIGHT, f.name) + (getattr(LOOSE, f.name) - getattr(TIGHT, f.name)) * s
        for f in fields(Layout)
    }
    return Layout(**vals)
