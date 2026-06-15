"""Tests for LaTeX engine detection (bundled tectonic + env override)."""

from __future__ import annotations

from app import latex_tools


def test_env_override_points_at_explicit_binary(tmp_path, monkeypatch):
    fake = tmp_path / "tectonic.exe"
    fake.write_bytes(b"")
    monkeypatch.setenv("RESUME_TAILOR_TECTONIC", str(fake))
    engine = latex_tools.detect_latex_engine()
    assert engine is not None
    assert engine.name == "tectonic"
    assert engine.path == str(fake)


def test_env_override_ignored_when_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("RESUME_TAILOR_TECTONIC", str(tmp_path / "nope.exe"))
    # Falls back to the bundled tools dir / PATH (don't assert a specific result,
    # just that a non-existent override doesn't crash or get returned).
    engine = latex_tools.detect_latex_engine()
    assert engine is None or engine.path != str(tmp_path / "nope.exe")
