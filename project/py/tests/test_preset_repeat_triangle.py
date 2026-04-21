from olik_font.constraints.presets import apply_repeat_triangle
from olik_font.geom import apply_affine_to_point
from olik_font.types import Affine, InstancePlacement


def _leaf(iid):
    return InstancePlacement(
        instance_id=iid, prototype_ref="proto:tree", transform=Affine.identity()
    )


def test_three_instances_placed_at_triangle_vertices():
    a, b, c = _leaf("inst:t1"), _leaf("inst:t2"), _leaf("inst:t3")
    resolved, _constraints = apply_repeat_triangle((a, b, c), glyph_bbox=(0, 0, 1024, 1024))
    assert len(resolved) == 3

    # instance 0: top-center — canonical center (512, 512) maps to around (512, 256)
    c0 = apply_affine_to_point(resolved[0].transform, (512.0, 512.0))
    assert abs(c0[0] - 512.0) < 1e-6
    assert abs(c0[1] - 256.0) < 1e-6

    # instance 1: bottom-left — around (256, 768)
    c1 = apply_affine_to_point(resolved[1].transform, (512.0, 512.0))
    assert abs(c1[0] - 256.0) < 1e-6
    assert abs(c1[1] - 768.0) < 1e-6

    # instance 2: bottom-right — around (768, 768)
    c2 = apply_affine_to_point(resolved[2].transform, (512.0, 512.0))
    assert abs(c2[0] - 768.0) < 1e-6
    assert abs(c2[1] - 768.0) < 1e-6


def test_constraints_include_repeat_and_pairwise_avoid_overlap():
    a, b, c = _leaf("inst:t1"), _leaf("inst:t2"), _leaf("inst:t3")
    _, constraints = apply_repeat_triangle((a, b, c), glyph_bbox=(0, 0, 1024, 1024))
    kinds = [type(x).__name__ for x in constraints]
    assert kinds.count("Repeat") == 1
    assert kinds.count("AvoidOverlap") == 3


def test_wrong_count_raises():
    import pytest

    a = _leaf("inst:t1")
    with pytest.raises(ValueError):
        apply_repeat_triangle((a,), glyph_bbox=(0, 0, 1024, 1024))
