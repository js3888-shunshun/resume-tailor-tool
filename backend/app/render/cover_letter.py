"""Render a `CoverLetterDocument` to LaTeX (Step 7).

Reuses the resume's Jinja env (LaTeX-safe delimiters + `latex_escape`); the body
paragraphs are escaped but not keyword-highlighted.
"""

from __future__ import annotations

from ..schemas import CoverLetterDocument, RenderContact
from .latex import _build_env, latex_escape


def _contact_line(c: RenderContact) -> str:
    parts = []
    if c.email:
        parts.append("Email: " + latex_escape(c.email))
    if c.phone:
        parts.append("Tel: " + latex_escape(c.phone))
    if c.location:
        parts.append(latex_escape(c.location))
    parts.extend(latex_escape(link) for link in c.links if link)
    return " | ".join(parts)


def render_cover_letter(doc: CoverLetterDocument) -> str:
    env = _build_env()
    template = env.get_template("cover_letter.tex.j2")
    return template.render(doc=doc, contact_line=_contact_line(doc.contact))
