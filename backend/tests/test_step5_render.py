"""M5 tests: LaTeX rendering. Pure functions, no LLM, no LaTeX engine needed."""

from __future__ import annotations

from app.render.latex import latex_escape, render_bullet, render_resume
from app.schemas import (
    RenderBullet,
    RenderContact,
    RenderEducation,
    RenderEntry,
    ResumeDocument,
    SkillGroup,
)


# ---- escaping ------------------------------------------------------------

def test_latex_escape_specials():
    out = latex_escape("Saved 30% & cut $1M for #1 team_x")
    assert out == r"Saved 30\% \& cut \$1M for \#1 team\_x"
    # No raw special left that would break compilation.
    for ch in "&%$#_":
        assert ch not in out.replace(r"\&", "").replace(r"\%", "").replace(
            r"\$", "").replace(r"\#", "").replace(r"\_", "")


def test_latex_escape_backslash_first():
    # A literal backslash must not double-escape the escapes we add.
    assert latex_escape(r"a\b") == r"a\textbackslash{}b"


# ---- keyword highlight ---------------------------------------------------

def test_render_bullet_wraps_keywords():
    b = RenderBullet(text="Built a RAG pipeline in Python", keywords=["RAG", "Python"])
    out = render_bullet(b)
    assert r"\hlkw{RAG}" in out
    assert r"\hlkw{Python}" in out


def test_render_bullet_case_insensitive_word_boundary():
    b = RenderBullet(text="Used pytorch, not pytorches", keywords=["PyTorch"])
    out = render_bullet(b)
    # Matches 'pytorch' (case-insensitive) but not the substring in 'pytorches'.
    assert r"\hlkw{pytorch}" in out
    assert "pytorches" in out and r"\hlkw{pytorch}es" not in out


def test_render_bullet_no_double_wrap_when_keyword_repeats_overlap():
    b = RenderBullet(text="machine learning and learning", keywords=["learning", "machine learning"])
    out = render_bullet(b)
    # Longest-first: 'machine learning' wrapped as a unit, not re-wrapped inside.
    assert r"\hlkw{machine learning}" in out
    assert out.count(r"\hlkw{") == 2  # the phrase + the standalone 'learning'


def test_render_bullet_highlight_off():
    b = RenderBullet(text="Built RAG, cut latency 30%", keywords=["RAG"])
    # highlight=False bolds nothing — not keywords, not numbers.
    assert render_bullet(b, highlight=False) == r"Built RAG, cut latency 30\%"


def test_render_bullet_bolds_numbers_and_metrics():
    b = RenderBullet(text="Cut latency 30% and cost $1.2M, served 12x at 1,000 QPS", keywords=[])
    out = render_bullet(b)
    assert r"\hlkw{30\%}" in out
    assert r"\hlkw{\$1.2M}" in out
    assert r"\hlkw{12x}" in out
    assert r"\hlkw{1,000}" in out


def test_render_bullet_number_inside_keyword_not_double_wrapped():
    # A keyword containing digits (S3) must not get its number re-bolded.
    b = RenderBullet(text="Stored data in S3 buckets", keywords=["S3"])
    out = render_bullet(b)
    assert r"\hlkw{S3}" in out
    assert out.count(r"\hlkw{") == 1


def test_render_bullet_escapes_then_highlights():
    b = RenderBullet(text="C# & SQL work", keywords=["C#"])
    out = render_bullet(b)
    assert r"\hlkw{C\#}" in out
    assert r"\&" in out


# ---- whole document ------------------------------------------------------

def _doc(**kw) -> ResumeDocument:
    base = dict(
        contact=RenderContact(name="Joy Sun", email="j@x.com", phone="123", location="NY"),
        education=[RenderEducation(school="Cornell", degree_line="MEng in DS", date="May 2026",
                                   details=["Coursework: ML, DL"])],
        skills=["Python", "PyTorch"],
        experiences=[RenderEntry(organization="ByteDance", title="DS Intern", location="Beijing",
                                 date_range="Feb 2025 – May 2025",
                                 bullets=[RenderBullet(text="Built RAG in Python", keywords=["RAG"])])],
        projects=[RenderEntry(kind="project", title="Text-to-SQL",
                              bullets=[RenderBullet(text="F1 of 0.665")])],
        projects_heading="Research Experience",
    )
    base.update(kw)
    return ResumeDocument(**base)


def test_render_resume_has_structure():
    tex = render_resume(_doc())
    assert tex.startswith(r"\documentclass")
    assert r"\begin{document}" in tex and r"\end{document}" in tex
    assert r"\newcommand{\hlkw}" in tex
    # Sections present.
    for sec in (r"\section{Education}", r"\section{Technical Skills}",
                r"\section{Professional Experience}", r"\section{Research Experience}"):
        assert sec in tex
    # Header + content.
    assert r"\textbf{Joy Sun}" in tex
    assert "Email: j@x.com" in tex
    assert r"\textbf{ByteDance} | \textit{DS Intern} | Beijing \hfill Feb 2025 – May 2025" in tex
    assert r"\hlkw{RAG}" in tex
    # Project (no org) uses bold title only.
    assert r"\textbf{Text-to-SQL}" in tex


def test_render_balanced_braces():
    # A crude but effective guard against template/escaping breakage.
    tex = render_resume(_doc(experiences=[
        RenderEntry(organization="Acme & Co", title="Eng", date_range="2024",
                    bullets=[RenderBullet(text="Cut cost by 30% for $1M_budget", keywords=[])])
    ]))
    assert tex.count("{") == tex.count("}")
    assert r"Acme \& Co" in tex
    # Metrics are auto-bolded; escaping survives inside the \hlkw wrap.
    assert r"\hlkw{30\%}" in tex and r"\hlkw{\$1M}" in tex and r"\_budget" in tex


def test_render_omits_empty_sections():
    tex = render_resume(_doc(education=[], skills=[], projects=[]))
    assert r"\section{Education}" not in tex
    assert r"\section{Technical Skills}" not in tex
    assert r"\section{Research Experience}" not in tex
    assert r"\section{Professional Experience}" in tex


def test_render_skills_line_escaped():
    tex = render_resume(_doc(skills=["C#", "A&B"]))
    assert r"C\#, A\&B" in tex


# ---- JD-tailored grouped skills + new header fields ----------------------

def test_render_grouped_skills_one_per_line():
    tex = render_resume(_doc(skill_groups=[
        SkillGroup(label="Programming", skills=["Python", "SQL"]),
        SkillGroup(label="ML & Data", skills=["PyTorch"]),
        SkillGroup(label="Tools", skills=["Git"]),
    ]))
    # Labels bold, skills listed, each group on its own row (no \hfill pairing).
    assert r"\textbf{Programming:} Python, SQL" in tex
    assert r"\textbf{ML \& Data:} PyTorch" in tex
    assert r"\textbf{Tools:} Git" in tex
    assert r"\hfill \textbf{" not in tex  # groups are not paired two-up
    # Balanced braces survive the grouped layout.
    assert tex.count("{") == tex.count("}")


def test_render_grouped_skills_override_flat():
    tex = render_resume(_doc(skills=["ZZZ"], skill_groups=[SkillGroup(label="Lang", skills=["Go"])]))
    assert r"\textbf{Lang:} Go" in tex
    assert "ZZZ" not in tex  # flat list ignored when groups present


def test_render_project_heading_title_first():
    tex = render_resume(_doc(projects=[RenderEntry(
        kind="project", title="Text-to-SQL", organization="Cornell Tech", date_range="Apr 2026",
        bullets=[RenderBullet(text="built it")])]))
    # Project: bold title first, then org, no italic.
    assert r"\textbf{Text-to-SQL} | Cornell Tech \hfill Apr 2026" in tex
    assert r"\textit{Text-to-SQL}" not in tex


def test_render_education_date_and_spaced_gpa():
    tex = render_resume(_doc(education=[RenderEducation(
        school="Cornell", location="New York, NY", degree_line="MEng in DS",
        gpa="3.9/4.0", date="May 2026")]))
    # School row carries the date (location dropped); GPA spaced after the major.
    assert r"\textbf{Cornell} \hfill May 2026" in tex
    assert r"\textit{MEng in DS} | GPA: 3.9/4.0" in tex
    assert "New York, NY" not in tex  # education location no longer rendered


def test_render_projects_first_swaps_order():
    kw = dict(
        experiences=[RenderEntry(organization="Acme", title="Eng", bullets=[RenderBullet(text="x")])],
        projects=[RenderEntry(kind="project", title="Proj", bullets=[RenderBullet(text="y")])],
        projects_heading="Research Experience",
    )
    default = render_resume(_doc(projects_first=False, **kw))
    swapped = render_resume(_doc(projects_first=True, **kw))
    assert default.index("Professional Experience") < default.index("Research Experience")
    assert swapped.index("Research Experience") < swapped.index("Professional Experience")
    assert swapped.count("{") == swapped.count("}")


def test_render_location_inline_in_contact():
    tex = render_resume(_doc(contact=RenderContact(
        name="J", email="j@x.com", phone="123", location="New York, NY, 10044")))
    # Location/address sits inline in the contact line: Email | Tel | address.
    assert "Email: j@x.com | Tel: 123 | New York, NY, 10044" in tex
    assert tex.count("{") == tex.count("}")
