"""Tests for the parameterised spacing layout (Step 6)."""

from __future__ import annotations

from dataclasses import fields

from app.render.layout import DEFAULT, LOOSE, TIGHT, Layout, layout_for


def test_layout_for_endpoints():
    assert layout_for(0.0) == TIGHT
    assert layout_for(1.0) == LOOSE


def test_layout_for_clamps_out_of_range():
    assert layout_for(-5) == TIGHT
    assert layout_for(9) == LOOSE


def test_layout_for_is_monotonic_between_bounds():
    mid = layout_for(0.5)
    for f in fields(Layout):
        lo, hi, m = getattr(TIGHT, f.name), getattr(LOOSE, f.name), getattr(mid, f.name)
        assert lo <= m <= hi


def test_as_template_formats_units():
    t = DEFAULT.as_template()
    assert t["line_spread"] == "1.000"            # unitless
    assert t["section_before"] == "4.00pt"        # pt unit appended
    assert t["item_itemsep"] == "0.00pt"
