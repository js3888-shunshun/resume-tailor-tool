"""Tests for the best-effort PDF compile wrapper (Step 5/6)."""

from __future__ import annotations

from pathlib import Path

import app.render.compile as compile_mod
from app.render.compile import CompileError, try_compile


def test_try_compile_swallows_arbitrary_errors(tmp_path, monkeypatch):
    # A non-CompileError during compile (e.g. the old GBK-decode TypeError) must
    # degrade to None, not bubble up and 500 the /render endpoint.
    def boom(*args, **kwargs):
        raise TypeError("can only concatenate str (not \"NoneType\") to str")

    monkeypatch.setattr(compile_mod, "compile_tex", boom)
    assert try_compile("whatever", tmp_path) is None


def test_try_compile_returns_none_on_compile_error(tmp_path, monkeypatch):
    def fail(*args, **kwargs):
        raise CompileError("no engine")

    monkeypatch.setattr(compile_mod, "compile_tex", fail)
    assert try_compile("whatever", tmp_path) is None


def test_try_compile_passes_through_path(tmp_path, monkeypatch):
    out = tmp_path / "resume.pdf"
    monkeypatch.setattr(compile_mod, "compile_tex", lambda *a, **k: out)
    assert try_compile("whatever", tmp_path) == out
