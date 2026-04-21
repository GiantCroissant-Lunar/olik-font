from olik_font.constraints.presets import apply_top_bottom
from olik_font.geom import apply_affine_to_point
from olik_font.types import Affine, InstancePlacement


def _leaf(iid, proto):
    return InstancePlacement(instance_id=iid, prototype_ref=proto, transform=Affine.identity())


def test_top_gets_upper_portion():
    top = _leaf("inst:T", "proto:a")
    bot = _leaf("inst:B", "proto:b")
    top_out, bot_out, constraints = apply_top_bottom(top, bot, glyph_bbox=(0, 0, 1024, 1024))
    _x, y1 = apply_affine_to_point(top_out.transform, (0.0, 1024.0))
    assert y1 < 512.0  # top doesn't cross halfway
    _x, y0 = apply_affine_to_point(bot_out.transform, (0.0, 0.0))
    assert y0 > 512.0
    kinds = [c.__class__.__name__ for c in constraints]
    assert "AlignX" in kinds
    assert "OrderY" in kinds
