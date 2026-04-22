from olik_font.constraints.presets import apply_enclose
from olik_font.geom import apply_affine_to_point
from olik_font.types import Affine, InstancePlacement


def _leaf(iid, proto):
    return InstancePlacement(instance_id=iid, prototype_ref=proto, transform=Affine.identity())


def test_inner_bbox_sits_inside_outer_with_padding():
    outer = _leaf("inst:O", "proto:box")
    inner = _leaf("inst:I", "proto:guts")
    outer_out, inner_out, constraints = apply_enclose(
        outer, inner, glyph_bbox=(0, 0, 1024, 1024), padding=100
    )

    # outer occupies full glyph
    p0 = apply_affine_to_point(outer_out.transform, (0.0, 0.0))
    p1 = apply_affine_to_point(outer_out.transform, (1024.0, 1024.0))
    assert p0 == (0.0, 0.0)
    assert p1 == (1024.0, 1024.0)

    # inner sits inside the padded frame
    ip0 = apply_affine_to_point(inner_out.transform, (0.0, 0.0))
    ip1 = apply_affine_to_point(inner_out.transform, (1024.0, 1024.0))
    assert ip0 == (100.0, 100.0)
    assert ip1 == (924.0, 924.0)

    kinds = [c.__class__.__name__ for c in constraints]
    assert "Inside" in kinds
    assert "AlignX" in kinds
    assert "AlignY" in kinds
