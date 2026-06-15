"""Compile a .tex string to PDF, if a LaTeX engine is available (Step 5/6).

Tectonic is preferred (single binary, auto-fetches packages); pdflatex is the
fallback and is run twice so \\hfill / references settle. Returns the PDF path or
raises CompileError with the captured log. When no engine is installed this
module is simply not called (the /render endpoint returns the .tex only).
"""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from ..latex_tools import detect_latex_engine


class CompileError(RuntimeError):
    def __init__(self, message: str, log: str = ""):
        super().__init__(message)
        self.log = log


def compile_tex(tex: str, out_dir: Path, stem: str = "resume") -> Path:
    """Compile `tex` to `out_dir/stem.pdf` and return the PDF path."""
    engine = detect_latex_engine()
    if engine is None:
        raise CompileError("No LaTeX engine installed (tectonic / pdflatex).")

    out_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        tex_file = tmp_path / f"{stem}.tex"
        tex_file.write_text(tex, encoding="utf-8")

        if engine.name == "tectonic":
            cmds = [[engine.path, "-o", str(tmp_path), str(tex_file)]]
        else:  # pdflatex: run twice
            base = [engine.path, "-interaction=nonstopmode", "-halt-on-error",
                    "-output-directory", str(tmp_path), str(tex_file)]
            cmds = [base, base]

        log = ""
        for cmd in cmds:
            proc = subprocess.run(cmd, capture_output=True, text=True, cwd=str(tmp_path))
            log += proc.stdout + proc.stderr

        pdf = tmp_path / f"{stem}.pdf"
        if not pdf.exists():
            raise CompileError(f"{engine.name} produced no PDF.", log=log)

        final = out_dir / f"{stem}.pdf"
        final.write_bytes(pdf.read_bytes())
        return final


def try_compile(tex: str, out_dir: Path, stem: str = "resume") -> Optional[Path]:
    """Best-effort compile: return the PDF path, or None if no engine / failure."""
    try:
        return compile_tex(tex, out_dir, stem=stem)
    except CompileError:
        return None
