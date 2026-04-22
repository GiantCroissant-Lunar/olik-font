"""fit_in_slot -- uniform-scale + per-anchor positioning inside a slot.

Used by the preset adapters in Plan 10.1 to stop non-uniform
stretching of canonical prototypes into slots of unequal aspect ratio.
"""

from __future__ import annotations

import pytest

from olik_font.geom import fit_in_slot

CANONICAL = (0.0, 0.0, 1024.0, 1024.0)


def test_identity_when_aspect_matches() -> None:
    """Square CANONICAL in a square dst -> returns dst unchanged for
    any anchor (uniform scale = 1, anchor position is irrelevant when
    the fitted dims exactly fill dst).
    """
    dst = (0.0, 0.0, 500.0, 500.0)
    for anchor in ("top-left", "top-center", "bottom-center", "center"):
        assert fit_in_slot(CANONICAL, dst, anchor) == dst


def test_top_left_anchor_in_tall_rectangular_slot() -> None:
    """Square CANONICAL in a 400x1024 slot (left_right[0] default).
    Uniform scale = min(400/1024, 1024/1024) = 0.3906...
    -> new dims = 400 x 400. Top-left anchor (y-up: HIGH y = top) puts
    the fitted square flush against the slot's left edge AND top edge.
    """
    slot = (0.0, 0.0, 400.0, 1024.0)
    result = fit_in_slot(CANONICAL, slot, "top-left")
    assert result[0] == 0.0
    assert abs(result[2] - 400.0) < 1e-9
    assert abs(result[3] - 1024.0) < 1e-9
    assert abs(result[1] - 624.0) < 1e-9


def test_top_center_anchor_in_wide_short_slot() -> None:
    """Square CANONICAL in a 1024x500 slot (top_bottom[0] default).
    Uniform scale = min(1024/1024, 500/1024) = 500/1024.
    -> new dims = 500 x 500. Top-center anchor centers x, flushes to
    high y.
    """
    slot = (0.0, 524.0, 1024.0, 1024.0)
    result = fit_in_slot(CANONICAL, slot, "top-center")
    assert abs(result[3] - 1024.0) < 1e-9
    assert abs(result[1] - 524.0) < 1e-9
    assert abs(result[0] - 262.0) < 1e-9
    assert abs(result[2] - 762.0) < 1e-9


def test_bottom_center_anchor_flushes_to_low_y() -> None:
    """Bottom-center in y-up convention: flushes to slot.y0 (LOW y)."""
    slot = (0.0, 0.0, 1024.0, 500.0)
    result = fit_in_slot(CANONICAL, slot, "bottom-center")
    assert abs(result[1] - 0.0) < 1e-9
    assert abs(result[3] - 500.0) < 1e-9
    assert abs(result[0] - 262.0) < 1e-9
    assert abs(result[2] - 762.0) < 1e-9


def test_center_anchor_puts_src_middle_of_dst() -> None:
    """Square CANONICAL in a 400x1024 slot with center anchor."""
    slot = (0.0, 0.0, 400.0, 1024.0)
    result = fit_in_slot(CANONICAL, slot, "center")
    assert abs(result[0] - 0.0) < 1e-9
    assert abs(result[2] - 400.0) < 1e-9
    assert abs(result[1] - 312.0) < 1e-9
    assert abs(result[3] - 712.0) < 1e-9


def test_nonsquare_src_preserves_aspect() -> None:
    """Tall-narrow src (1:2) in a wide-short dst (2:1).
    src = (0, 0, 100, 200); dst = (0, 0, 400, 200).
    scale = min(400/100, 200/200) = 2. new = 200x400.
    ...wait, new_h = 200*2 = 400 but dst_h = 200 -- overflows.
    Recompute: scale = min(4.0, 1.0) = 1.0. new = 100x200.
    Top-left: x0=0, x1=100, y1=200, y0=0.
    """
    src = (0.0, 0.0, 100.0, 200.0)
    dst = (0.0, 0.0, 400.0, 200.0)
    result = fit_in_slot(src, dst, "top-left")
    assert abs(result[0] - 0.0) < 1e-9
    assert abs(result[2] - 100.0) < 1e-9
    assert abs(result[1] - 0.0) < 1e-9
    assert abs(result[3] - 200.0) < 1e-9


def test_zero_width_src_raises() -> None:
    with pytest.raises(ValueError):
        fit_in_slot((10.0, 0.0, 10.0, 100.0), CANONICAL, "center")


def test_zero_height_src_raises() -> None:
    with pytest.raises(ValueError):
        fit_in_slot((0.0, 100.0, 100.0, 100.0), CANONICAL, "center")


def test_unknown_anchor_raises() -> None:
    with pytest.raises(ValueError, match="anchor"):
        fit_in_slot(CANONICAL, CANONICAL, "nonsense")  # type: ignore[arg-type]
