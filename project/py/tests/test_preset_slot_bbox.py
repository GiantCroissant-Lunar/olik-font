"""slot_bbox — shared helper returning the y-up slot bbox for each preset.

Regression guard: slot_bbox output for each preset must equal the bbox
used internally by the corresponding apply_* renderer. Plan 09.1 fixed
y-up semantics for top_bottom and repeat_triangle; those fixes must
survive this refactor.
"""

from __future__ import annotations

import pytest

from olik_font.constraints.presets import slot_bbox

CANONICAL_BBOX = (0.0, 0.0, 1024.0, 1024.0)


def test_left_right_slot_0_is_left_half() -> None:
    bbox = slot_bbox("left_right", n_components=2, slot_idx=0, glyph_bbox=CANONICAL_BBOX)
    # weight_l default = 400/1024 → split_x = 400
    assert bbox == (0.0, 0.0, 400.0, 1024.0)


def test_left_right_slot_1_is_right_half_with_gap() -> None:
    bbox = slot_bbox("left_right", n_components=2, slot_idx=1, glyph_bbox=CANONICAL_BBOX)
    # gap default = 20 → right starts at 420
    assert bbox == (420.0, 0.0, 1024.0, 1024.0)


def test_top_bottom_slot_0_is_visual_top_at_high_y() -> None:
    """Plan 09.1 regression guard: visual top lives at HIGH y after the
    render-time flip."""
    bbox = slot_bbox("top_bottom", n_components=2, slot_idx=0, glyph_bbox=CANONICAL_BBOX)
    _, y0, _, y1 = bbox
    assert y1 == 1024.0  # top of slot touches top of glyph (HIGH y)
    assert y0 > 512.0  # slot starts above mid


def test_top_bottom_slot_1_is_visual_bottom_at_low_y() -> None:
    bbox = slot_bbox("top_bottom", n_components=2, slot_idx=1, glyph_bbox=CANONICAL_BBOX)
    _, y0, _, y1 = bbox
    assert y0 == 0.0  # bottom of slot touches bottom of glyph (LOW y)
    assert y1 == pytest.approx(522.24)


def test_enclose_slot_0_is_outer_full_bbox() -> None:
    bbox = slot_bbox("enclose", n_components=2, slot_idx=0, glyph_bbox=CANONICAL_BBOX)
    assert bbox == CANONICAL_BBOX


def test_enclose_slot_1_is_inner_padded() -> None:
    bbox = slot_bbox("enclose", n_components=2, slot_idx=1, glyph_bbox=CANONICAL_BBOX)
    # padding default = 100
    assert bbox == (100.0, 100.0, 924.0, 924.0)


def test_repeat_triangle_slot_0_is_top_center_at_high_y() -> None:
    """Plan 09.1 regression guard: triangle's top-center position sits
    at HIGH y."""
    bbox = slot_bbox("repeat_triangle", n_components=3, slot_idx=0, glyph_bbox=CANONICAL_BBOX)
    _, y0, _, y1 = bbox
    assert y1 == 1024.0  # top edge of the top-center cell reaches glyph top
    assert y0 == 512.0  # cell is 0.5 * 1024 tall


def test_repeat_triangle_slots_1_2_are_bottom() -> None:
    left = slot_bbox("repeat_triangle", n_components=3, slot_idx=1, glyph_bbox=CANONICAL_BBOX)
    right = slot_bbox("repeat_triangle", n_components=3, slot_idx=2, glyph_bbox=CANONICAL_BBOX)
    assert left[1] == 0.0
    assert right[1] == 0.0
    assert left[3] == 512.0
    assert right[3] == 512.0
    # bottom-left strictly left of bottom-right
    assert left[0] < right[0]


def test_unknown_preset_raises() -> None:
    with pytest.raises(ValueError, match="unknown preset"):
        slot_bbox("nonsense", n_components=2, slot_idx=0, glyph_bbox=CANONICAL_BBOX)


def test_slot_idx_out_of_range_raises() -> None:
    with pytest.raises(ValueError, match="slot_idx"):
        slot_bbox("left_right", n_components=2, slot_idx=5, glyph_bbox=CANONICAL_BBOX)
