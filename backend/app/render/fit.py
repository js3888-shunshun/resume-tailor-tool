"""Step 6: land the resume on exactly one page by tuning typography only.

Deterministic, zero-LLM. We compile the document at varying spacing `scale`s and
count pages with pypdf, searching for the layout that fills the page as fully as
possible without spilling onto a second page:

- If even the TIGHTEST layout overflows, the content is genuinely too long — we
  return the tightest version and report `overflow` (the UI asks the user to trim).
- If even the LOOSEST layout still fits, we use it (it fills the most).
- Otherwise we binary-search the largest `scale` that stays at one page.

The winning `.tex` is compiled to `out_dir/<stem>.pdf` as the final artifact.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from ..latex_tools import detect_latex_engine
from ..schemas import ResumeDocument
from .compile import count_pages, try_compile
from .latex import render_resume
from .layout import DEFAULT, layout_for

log = logging.getLogger("resume_tailor.step6")

_PROBE_STEM = "_fit_probe"


@dataclass
class FitResult:
    tex: str
    pages: int                 # page count of the chosen layout (0 if unknown)
    scale: float               # spacing scale used (0=tight .. 1=loose)
    status: str                # "fit" | "overflow" | "no_engine" | "error"
    pdf_available: bool


def fit_to_one_page(
    doc: ResumeDocument,
    out_dir: Path,
    *,
    max_iter: int = 5,
    stem: str = "resume",
) -> FitResult:
    """Search spacing for a one-page fit and compile the winner to out_dir/stem.pdf."""
    out_dir.mkdir(parents=True, exist_ok=True)
    engine = detect_latex_engine()
    if engine is None:
        # No engine: just hand back the default-spacing .tex, no PDF.
        return FitResult(render_resume(doc, DEFAULT), 0, 0.0, "no_engine", False)

    def measure(tex: str) -> Optional[int]:
        pdf = try_compile(tex, out_dir, stem=_PROBE_STEM)
        return count_pages(pdf) if pdf else None

    def finalize(tex: str, pages: int, scale: float, status: str) -> FitResult:
        pdf = try_compile(tex, out_dir, stem=stem)
        _cleanup_probe(out_dir)
        return FitResult(tex, pages, scale, status, pdf is not None)

    # 1) Tightest — can the content fit one page at all?
    tight_tex = render_resume(doc, layout_for(0.0))
    pt = measure(tight_tex)
    if pt is None:
        _cleanup_probe(out_dir)
        return FitResult(tight_tex, 0, 0.0, "error", False)
    if pt > 1:
        log.info("Step6: content overflows one page even at tightest spacing (%d pages)", pt)
        return finalize(tight_tex, pt, 0.0, "overflow")

    # 2) Loosest — if it still fits, use it (fills the most).
    loose_tex = render_resume(doc, layout_for(1.0))
    if measure(loose_tex) == 1:
        log.info("Step6: fits at loosest spacing; using it to fill the page")
        return finalize(loose_tex, 1, 1.0, "fit")

    # 3) Binary-search the largest scale that stays on one page.
    lo, hi = 0.0, 1.0
    best_tex, best_scale = tight_tex, 0.0
    for _ in range(max_iter):
        mid = (lo + hi) / 2
        tex = render_resume(doc, layout_for(mid))
        if measure(tex) == 1:
            best_tex, best_scale = tex, mid
            lo = mid
        else:
            hi = mid
    log.info("Step6: one-page fit at spacing scale=%.3f", best_scale)
    return finalize(best_tex, 1, best_scale, "fit")


def _cleanup_probe(out_dir: Path) -> None:
    try:
        (out_dir / f"{_PROBE_STEM}.pdf").unlink(missing_ok=True)
    except OSError:
        pass
