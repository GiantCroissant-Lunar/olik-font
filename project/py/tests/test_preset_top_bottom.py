from olik_font.constraints.presets import apply_top_bottom
from olik_font.geom import apply_affine_to_point
from olik_font.types import Affine, InstancePlacement


def _leaf(iid, proto):
    return InstancePlacement(instance_id=iid, prototype_ref=proto, transform=Affine.identity())


def test_top_slot_top_center_anchor_flushes_to_upper_edge():
    """Default slot_0 for top_bottom: x=[0,1024], y=[~522, 1024]
    (y-up: HIGH y = visual top). Width 1024, height ~502. Uniform fit
    of square canonical: 502x502, x-centered, y flush to top.
    """
    top = _leaf("inst:T", "proto:a")
    bot = _leaf("inst:B", "proto:b")
    top_out, _bot_out, _c = apply_top_bottom(top, bot, glyph_bbox=(0, 0, 1024, 1024))
    # canonical (0, 1024) (visual top-left of the canonical) -> top-center
    # of the slot: y = slot.y1 = 1024; x = centered within the fitted
    # width derived from slot_0's actual height.
    x0, y1 = apply_affine_to_point(top_out.transform, (0.0, 1024.0))
    assert abs(y1 - 1024.0) < 1e-3
    # With the current pinned slot math, slot_0 is (0, 542.24, 1024, 1024),
    # so new_w = new_h = 481.76 and x0 = 512 - 240.88 = 271.12.
    assert abs(x0 - 271.12) < 1e-3


def test_bottom_slot_bottom_center_anchor_flushes_to_lower_edge():
    top = _leaf("inst:T", "proto:a")
    bot = _leaf("inst:B", "proto:b")
    _top_out, bot_out, _c = apply_top_bottom(top, bot, glyph_bbox=(0, 0, 1024, 1024))
    # canonical (0, 0) (visual bottom-left of canonical) -> bottom-left
    # of the fitted sub-bbox flush to slot.y0 = 0.
    x0, y0 = apply_affine_to_point(bot_out.transform, (0.0, 0.0))
    assert abs(y0 - 0.0) < 1e-3
    # slot_1 is (0, 0, 1024, 522.24), so new_w = new_h = 522.24 and
    # x0 = 512 - 261.12 = 250.88.
    assert abs(x0 - 250.88) < 1e-3


def test_top_and_bottom_do_not_overlap_in_y():
    """Regression guard: top's y-range stays above bottom's y-range."""
    top = _leaf("inst:T", "proto:a")
    bot = _leaf("inst:B", "proto:b")
    top_out, bot_out, _ = apply_top_bottom(top, bot, glyph_bbox=(0, 0, 1024, 1024))
    _, top_y_low = apply_affine_to_point(top_out.transform, (0.0, 0.0))
    _, bot_y_hi = apply_affine_to_point(bot_out.transform, (0.0, 1024.0))
    assert bot_y_hi < top_y_low


def test_constraints_emitted_unchanged():
    top = _leaf("inst:T", "proto:a")
    bot = _leaf("inst:B", "proto:b")
    _, _, constraints = apply_top_bottom(top, bot, glyph_bbox=(0, 0, 1024, 1024))
    kinds = [c.__class__.__name__ for c in constraints]
    assert "AlignX" in kinds
    assert "OrderY" in kinds
