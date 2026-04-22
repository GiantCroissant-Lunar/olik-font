from olik_font.constraints.presets import apply_left_right
from olik_font.geom import apply_affine_to_point
from olik_font.types import Affine, InstancePlacement


def _leaf(instance_id: str, proto: str) -> InstancePlacement:
    return InstancePlacement(
        instance_id=instance_id,
        prototype_ref=proto,
        transform=Affine.identity(),
    )


def test_left_slot_top_left_anchor_puts_square_canonical_flush_top_left():
    """CANONICAL is square (1024x1024). Default slot_0 is (0, 0, 400,
    1024) — tall rectangle. Uniform fit: 400x400 flush to the slot's
    left edge and top edge (y-up: high y = top).
    """
    left = _leaf("inst:L", "proto:a")
    right = _leaf("inst:R", "proto:b")
    l_out, _r_out, _constraints = apply_left_right(left, right, glyph_bbox=(0, 0, 1024, 1024))
    # canonical (0, 1024) is the top-left corner; should map to
    # the top-left corner of the fitted sub-bbox inside slot 0.
    x0, y1 = apply_affine_to_point(l_out.transform, (0.0, 1024.0))
    assert abs(x0 - 0.0) < 1e-6
    assert abs(y1 - 1024.0) < 1e-6
    # canonical (1024, 0) is the bottom-right corner of canonical →
    # maps to x = 400 (slot width), y = 1024 - 400 = 624.
    x1, y0 = apply_affine_to_point(l_out.transform, (1024.0, 0.0))
    assert abs(x1 - 400.0) < 1e-6
    assert abs(y0 - 624.0) < 1e-6


def test_right_slot_top_left_anchor_flush_against_gap():
    """Slot 1 after default weight_l + gap=20 starts at x=420.
    The right slot is (420, 0, 1024, 1024) — slightly wider than tall
    (604 wide, 1024 tall). Uniform fit: 604x604, flush top-left of
    slot → (420, 420, 1024, 1024)."""
    left = _leaf("inst:L", "proto:a")
    right = _leaf("inst:R", "proto:b")
    _l_out, r_out, _ = apply_left_right(left, right, glyph_bbox=(0, 0, 1024, 1024))
    # canonical (0, 1024) (top-left) → slot top-left corner (420, 1024)
    x0, y1 = apply_affine_to_point(r_out.transform, (0.0, 1024.0))
    assert abs(x0 - 420.0) < 1e-6
    assert abs(y1 - 1024.0) < 1e-6
    # canonical (1024, 0) → (420 + 604, 1024 - 604) = (1024, 420)
    x1, y0 = apply_affine_to_point(r_out.transform, (1024.0, 0.0))
    assert abs(x1 - 1024.0) < 1e-6
    assert abs(y0 - 420.0) < 1e-6


def test_constraints_emitted_unchanged():
    """Plan 10.1 does not change constraint emission."""
    left = _leaf("inst:L", "proto:a")
    right = _leaf("inst:R", "proto:b")
    _, _, constraints = apply_left_right(left, right, glyph_bbox=(0, 0, 1024, 1024))
    kinds = [c.__class__.__name__ for c in constraints]
    assert "AlignY" in kinds
    assert "OrderX" in kinds
    assert "AnchorDistance" in kinds


def test_weight_l_override_is_ignored_per_plan_09_1():
    """Plan 09.1 pinned weight_l/gap to module-level constants for
    lockstep with variant_match's slot prediction. Plan 10.1
    preserves that behavior: passing a different weight_l has no
    effect on the fitted bbox.
    """
    left = _leaf("inst:L", "proto:a")
    right = _leaf("inst:R", "proto:b")
    l_out_default, _, _ = apply_left_right(left, right, glyph_bbox=(0, 0, 1024, 1024))
    l_out_overridden, _, _ = apply_left_right(
        left, right, glyph_bbox=(0, 0, 1024, 1024), weight_l=0.5, gap=0.0
    )
    # Same transform for both.
    p_default = apply_affine_to_point(l_out_default.transform, (0.0, 0.0))
    p_overridden = apply_affine_to_point(l_out_overridden.transform, (0.0, 0.0))
    assert p_default == p_overridden
