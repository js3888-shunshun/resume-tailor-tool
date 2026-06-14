"""Detection of a usable LaTeX engine (tectonic preferred, pdflatex fallback).

Used at startup to warn the user early (ROADMAP requirement) and later by the
Step 6 compile loop to pick an engine.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from typing import Optional


@dataclass
class LatexEngine:
    name: str  # "tectonic" | "pdflatex"
    path: str


def detect_latex_engine() -> Optional[LatexEngine]:
    """Return the first available LaTeX engine, or None if none found."""
    for name in ("tectonic", "pdflatex"):
        path = shutil.which(name)
        if path:
            return LatexEngine(name=name, path=path)
    return None


INSTALL_HINT = (
    "No LaTeX engine found (tectonic / pdflatex).\n"
    "  Recommended: install Tectonic (single binary, auto-fetches packages):\n"
    "    Windows (winget):  winget install TectonicProject.Tectonic\n"
    "    or scoop:          scoop install tectonic\n"
    "  Alternative: install MiKTeX (provides pdflatex): https://miktex.org/download\n"
    "  Resume PDF generation (Step 5/6) is disabled until one is installed."
)
