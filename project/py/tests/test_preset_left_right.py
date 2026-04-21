from olik_font.constraints.presets import apply_left_right
from olik_font.geom import apply_affine_to_point
from olik_font.types import Affine, InstancePlacement


def _leaf(instance_id: str, proto: str) -> InstancePlacement:
    return InstancePlacement(
        instance_id=instance_id,
        prototype_ref=proto,
        transform=Affine.identity(),
    )


def test_default_weights_put_left_in_left_40pct():
    left = _leaf("inst:L", "proto:a")
    right = _leaf("inst:R", "proto:b")
    l_out, r_out, _constraints = apply_left_right(left, right, glyph_bbox=(0, 0, 1024, 1024))
    # Left child: canonical (0,0,1024,1024) → placed (0, 0, 400, 1024)
    assert apply_affine_to_point(l_out.transform, (0.0, 0.0)) == (0.0, 0.0)
    x1, _y = apply_affine_to_point(l_out.transform, (1024.0, 0.0))
    assert abs(x1 - 400.0) < 1e-6
    # Right child: canonical (0,0) → placed (420, 0) with default gap 20
    x0r, _ = apply_affine_to_point(r_out.transform, (0.0, 0.0))
    assert abs(x0r - 420.0) < 1e-6


def test_constraints_emitted():
    left = _leaf("inst:L", "proto:a")
    right = _leaf("inst:R", "proto:b")
    _, _, constraints = apply_left_right(left, right, glyph_bbox=(0, 0, 1024, 1024))
    kinds = [c.__class__.__name__ for c in constraints]
    assert "AlignY" in kinds
    assert "OrderX" in kinds
    assert "AnchorDistance" in kinds


def test_custom_weight():
    left = _leaf("inst:L", "proto:a")
    right = _leaf("inst:R", "proto:b")
    l_out, _r_out, _ = apply_left_right(
        left, right, glyph_bbox=(0, 0, 1024, 1024), weight_l=0.5, gap=0.0
    )
    x1, _ = apply_affine_to_point(l_out.transform, (1024.0, 0.0))
    assert abs(x1 - 512.0) < 1e-6
