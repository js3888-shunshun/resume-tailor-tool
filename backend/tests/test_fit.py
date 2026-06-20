"""Tests for the Step 6 one-page fit search.

The LaTeX engine is mocked: a fake compile records the rendered tex and a fake
page-counter models "content height" as a threshold on the layout's line_spread
(looser spacing -> taller -> spills to page 2 once it crosses the threshold).
"""

from __future__ import annotations

import types

import pytest

import app.render.fit as fit
from app.render.layout import LOOSE, TIGHT
from app.schemas import RenderContact, ResumeDocument

DOC = ResumeDocument(contact=RenderContact(name="T"))


def _install_fake_engine(monkeypatch, threshold: float):
    """Wire fit's compile/count/render to a height model: fits iff line_spread<=threshold."""
    state: dict[str, str] = {}

    monkeypatch.setattr(fit, "detect_latex_engine",
                        lambda: types.SimpleNamespace(name="tectonic", path="x"))
    # Encode the layout's line_spread into the "tex" so the counter can read it.
    monkeypatch.setattr(fit, "render_resume",
                        lambda doc, layout: f"ls={layout.line_spread:.4f}")

    def fake_try_compile(tex, out_dir, stem="resume"):
        state["last"] = tex
        return out_dir / f"{stem}.pdf"

    def fake_count_pages(pdf):
        ls = float(state["last"].split("=")[1])
        return 1 if ls <= threshold + 1e-9 else 2

    monkeypatch.setattr(fit, "try_compile", fake_try_compile)
    monkeypatch.setattr(fit, "count_pages", fake_count_pages)
    return state


def test_no_engine_returns_tex_only(monkeypatch, tmp_path):
    monkeypatch.setattr(fit, "detect_latex_engine", lambda: None)
    res = fit.fit_to_one_page(DOC, tmp_path)
    assert res.status == "no_engine"
    assert res.pdf_available is False
    assert res.tex  # default-spacing tex still returned


def test_overflow_even_at_tightest(monkeypatch, tmp_path):
    # threshold below TIGHT.line_spread -> nothing fits.
    _install_fake_engine(monkeypatch, threshold=TIGHT.line_spread - 0.01)
    res = fit.fit_to_one_page(DOC, tmp_path)
    assert res.status == "overflow"
    assert res.pages == 2
    assert res.scale == 0.0
    assert res.pdf_available is True  # tightest still compiled (just 2 pages)


def test_uses_loosest_when_it_fits(monkeypatch, tmp_path):
    # threshold above LOOSE.line_spread -> even loosest fits; should pick scale 1.
    _install_fake_engine(monkeypatch, threshold=LOOSE.line_spread + 0.01)
    res = fit.fit_to_one_page(DOC, tmp_path)
    assert res.status == "fit"
    assert res.scale == 1.0
    assert res.pages == 1


def test_binary_search_fills_without_overflow(monkeypatch, tmp_path):
    # Mid threshold: the chosen layout must fit (line_spread <= threshold) and be
    # close to it (filling the page), never exceeding it.
    threshold = (TIGHT.line_spread + LOOSE.line_spread) / 2
    state = _install_fake_engine(monkeypatch, threshold=threshold)
    res = fit.fit_to_one_page(DOC, tmp_path, max_iter=8)
    assert res.status == "fit"
    assert res.pages == 1
    chosen_ls = float(state["last"].split("=")[1])
    assert chosen_ls <= threshold + 1e-9          # fits
    assert threshold - chosen_ls < 0.05           # but near the limit (page filled)
    assert 0.0 < res.scale < 1.0


def test_probe_file_is_cleaned_up(monkeypatch, tmp_path):
    _install_fake_engine(monkeypatch, threshold=1.10)
    # The probe stem is derived from the (default) stem; cleanup must remove it.
    (tmp_path / "_probe_resume.pdf").write_bytes(b"%PDF-1.4")
    fit.fit_to_one_page(DOC, tmp_path)
    assert not (tmp_path / "_probe_resume.pdf").exists()
