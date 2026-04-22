from olik_font.constraints.presets import apply_top_bottom
from olik_font.geom import apply_affine_to_point
from olik_font.types import Affine, InstancePlacement


def _leaf(iid, proto):
    return InstancePlacement(instance_id=iid, prototype_ref=proto, transform=Affine.identity())


def test_top_gets_upper_portion():
    # y-up convention: y=1024 is visual top, y=0 is visual bottom. The
    # VISUAL top slot therefore occupies HIGH y; the visual bottom slot
    # occupies LOW y. A stroke in the top slot's canonical (0, 0) corner
    # maps to a point whose y lies ABOVE the midpoint; a stroke in the
    # bottom slot's canonical (0, 1024) corner maps to a point BELOW.
    top = _leaf("inst:T", "proto:a")
    bot = _leaf("inst:B", "proto:b")
    top_out, bot_out, constraints = apply_top_bottom(top, bot, glyph_bbox=(0, 0, 1024, 1024))
    # Default weight_top=0.49 + gap=20 puts the split near the midline.
    # Assert the two bboxes are non-overlapping and correctly ordered
    # (top sits above bottom in y-up coords).
    _x, y_top_lo = apply_affine_to_point(top_out.transform, (0.0, 0.0))
    _x, y_top_hi = apply_affine_to_point(top_out.transform, (0.0, 1024.0))
    _x, y_bot_lo = apply_affine_to_point(bot_out.transform, (0.0, 0.0))
    _x, y_bot_hi = apply_affine_to_point(bot_out.transform, (0.0, 1024.0))
    assert y_bot_hi < y_top_lo  # gap between slots
    assert y_top_hi > 1000  # top reaches the upper edge
    assert y_bot_lo < 20  # bottom reaches the lower edge
    kinds = [c.__class__.__name__ for c in constraints]
    assert "AlignX" in kinds
    assert "OrderY" in kinds
