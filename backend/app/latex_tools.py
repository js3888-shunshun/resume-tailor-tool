"""Detection of a usable LaTeX engine (tectonic preferred, pdflatex fallback).

Used at startup to warn the user early (ROADMAP requirement) and later by the
Step 6 compile loop to pick an engine.
"""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

# A tectonic.exe dropped here (single binary, no installer) is used if present,
# so PDF export works without a system-wide LaTeX install / PATH changes.
BUNDLED_TOOLS_DIR = Path(__file__).resolve().parents[1] / "tools"


@dataclass
class LatexEngine:
    name: str  # "tectonic" | "pdflatex"
    path: str


def _bundled_tectonic() -> Optional[str]:
    # Explicit override wins, then the bundled tools dir.
    override = os.getenv("RESUME_TAILOR_TECTONIC", "").strip()
    if override and Path(override).exists():
        return override
    for name in ("tectonic.exe", "tectonic"):
        candidate = BUNDLED_TOOLS_DIR / name
        if candidate.exists():
            return str(candidate)
    return None


def detect_latex_engine() -> Optional[LatexEngine]:
    """Return the first available LaTeX engine, or None if none found.

    Order: a bundled tectonic binary (backend/tools or RESUME_TAILOR_TECTONIC),
    then anything on PATH (tectonic, then pdflatex).
    """
    bundled = _bundled_tectonic()
    if bundled:
        return LatexEngine(name="tectonic", path=bundled)
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
