r"""LaTeX rendering for the resume (Step 5).

`render_resume(doc)` turns a self-contained `ResumeDocument` into a `.tex`
string using a Jinja2 template. Two concerns live here:

1. **Escaping** — `latex_escape` neutralises LaTeX special characters so a bullet
   like "Saved 30% & cut $1M" can't break compilation.
2. **Keyword highlight** — `render_bullet` escapes a bullet, then wraps each
   matched JD keyword in `\hlkw{...}` (defined as bold in the template preamble)
   for ATS emphasis.

The Jinja2 environment uses LaTeX-safe delimiters (`\VAR{}`, `\BLOCK{}`) so the
template itself stays valid-ish LaTeX and `{}`/`%` don't clash with Jinja.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

import jinja2

from ..schemas import RenderBullet, RenderEntry, ResumeDocument

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"

# Single-pass map so replacements (which themselves contain `{`, `}`, `\`) are
# never re-escaped by a later pass.
_ESCAPES = {
    "\\": r"\textbackslash{}",
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
}
_ESCAPE_RE = re.compile("|".join(re.escape(c) for c in _ESCAPES))


def latex_escape(value) -> str:
    """Escape LaTeX special characters in arbitrary text."""
    text = "" if value is None else str(value)
    return _ESCAPE_RE.sub(lambda m: _ESCAPES[m.group(0)], text)


def render_bullet(bullet: RenderBullet, highlight: bool = True) -> str:
    """Escape a bullet, then bold its matched JD keywords via \\hlkw."""
    escaped = latex_escape(bullet.text)
    if not highlight or not bullet.keywords:
        return escaped
    # Longest keywords first so e.g. "machine learning" wins over "learning".
    for kw in sorted({k for k in bullet.keywords if k.strip()}, key=len, reverse=True):
        esc_kw = latex_escape(kw)
        # Word-boundary on alphanumerics; case-insensitive. Don't re-wrap text
        # already inside an \hlkw{...} we just added.
        pattern = re.compile(
            r"(?<![A-Za-z0-9])" + re.escape(esc_kw) + r"(?![A-Za-z0-9])",
            re.IGNORECASE,
        )
        escaped = _sub_outside_hlkw(pattern, escaped)
    return escaped


def _sub_outside_hlkw(pattern: re.Pattern, text: str) -> str:
    """Apply `pattern` -> \\hlkw{match}, skipping spans already inside \\hlkw{}."""
    out, idx = [], 0
    for guard in re.finditer(r"\\hlkw\{[^}]*\}", text):
        out.append(pattern.sub(lambda m: r"\hlkw{" + m.group(0) + "}", text[idx:guard.start()]))
        out.append(guard.group(0))  # leave existing highlight untouched
        idx = guard.end()
    out.append(pattern.sub(lambda m: r"\hlkw{" + m.group(0) + "}", text[idx:]))
    return "".join(out)


def _entry_head(entry: RenderEntry) -> str:
    """Build the bold title line for one experience/project, omitting blanks.

    experience: \\textbf{org} | \\textit{title} | location \\hfill dates
    project:    \\textbf{title} | org \\hfill dates
    """
    if entry.kind == "project":
        left = [r"\textbf{%s}" % latex_escape(entry.title)]
        if entry.organization:
            left.append(latex_escape(entry.organization))
        if entry.location:
            left.append(latex_escape(entry.location))
    else:
        left = [r"\textbf{%s}" % latex_escape(entry.organization or entry.title)]
        if entry.organization and entry.title:
            left.append(r"\textit{%s}" % latex_escape(entry.title))
        if entry.location:
            left.append(latex_escape(entry.location))
    head = " | ".join(left)
    if entry.date_range:
        head += r" \hfill " + latex_escape(entry.date_range)
    return head


def _contact_line(doc: ResumeDocument) -> str:
    parts = []
    if doc.contact.email:
        parts.append("Email: " + latex_escape(doc.contact.email))
    if doc.contact.phone:
        parts.append("Tel: " + latex_escape(doc.contact.phone))
    if doc.contact.location:
        parts.append(latex_escape(doc.contact.location))
    parts.extend(latex_escape(link) for link in doc.contact.links if link)
    return " | ".join(parts)


def _skills_line(skills: Iterable[str]) -> str:
    return ", ".join(latex_escape(s) for s in skills if str(s).strip())


def _skills_block(doc: ResumeDocument) -> str:
    """The body of the Technical Skills section.

    With JD-tailored `skill_groups`, render one labeled group per line
    (\\textbf{label:} a, b, c), so each category stands on its own row.
    Otherwise fall back to a single flat comma list.
    """
    groups = [g for g in doc.skill_groups if g.label.strip() and g.skills]
    if not groups:
        return _skills_line(doc.skills)
    rows = [
        r"\textbf{%s:} %s" % (latex_escape(g.label), _skills_line(g.skills))
        for g in groups
    ]
    return " \\\\\n    ".join(rows)


def _build_env() -> jinja2.Environment:
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(TEMPLATES_DIR)),
        block_start_string=r"\BLOCK{",
        block_end_string="}",
        variable_start_string=r"\VAR{",
        variable_end_string="}",
        comment_start_string=r"\#{",
        comment_end_string="}",
        trim_blocks=True,
        lstrip_blocks=True,
        autoescape=False,
        keep_trailing_newline=True,
    )
    env.filters["latex"] = latex_escape
    env.filters["entry_head"] = _entry_head
    return env


def render_resume(doc: ResumeDocument) -> str:
    """Render a complete `ResumeDocument` to a LaTeX source string."""
    env = _build_env()
    # `bullet` needs the per-document highlight flag, so bind it here.
    env.filters["bullet"] = lambda b: render_bullet(b, highlight=doc.highlight)
    template = env.get_template("resume.tex.j2")
    return template.render(
        doc=doc,
        contact_line=_contact_line(doc),
        skills_block=_skills_block(doc),
    )
