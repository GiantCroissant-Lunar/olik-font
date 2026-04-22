from olik_font.constraints.presets import apply_repeat_triangle
from olik_font.geom import apply_affine_to_point
from olik_font.types import Affine, InstancePlacement


def _leaf(iid):
    return InstancePlacement(
        instance_id=iid, prototype_ref="proto:tree", transform=Affine.identity()
    )


def test_three_instances_centered_inside_tall_triangle_cells_with_aspect_preserved():
    # Force non-square repeat_triangle cells so Plan 10.1's centered
    # aspect-preserving fit is observable. In a 1024x2048 glyph, each
    # triangle cell is 512x1024. CANONICAL is square, so each instance
    # must fit as a 512x512 square centered vertically inside its cell.
    a, b, c = _leaf("inst:t1"), _leaf("inst:t2"), _leaf("inst:t3")
    resolved, _constraints = apply_repeat_triangle((a, b, c), glyph_bbox=(0, 0, 1024, 2048))
    assert len(resolved) == 3

    # instance 0: top-center cell (256, 1024, 768, 2048) ->
    # fitted square (256, 1280, 768, 1792).
    p0_lo = apply_affine_to_point(resolved[0].transform, (0.0, 0.0))
    p0_hi = apply_affine_to_point(resolved[0].transform, (1024.0, 1024.0))
    assert p0_lo == (256.0, 1280.0)
    assert p0_hi == (768.0, 1792.0)

    # instance 1: bottom-left cell (0, 0, 512, 1024) ->
    # fitted square (0, 256, 512, 768).
    p1_lo = apply_affine_to_point(resolved[1].transform, (0.0, 0.0))
    p1_hi = apply_affine_to_point(resolved[1].transform, (1024.0, 1024.0))
    assert p1_lo == (0.0, 256.0)
    assert p1_hi == (512.0, 768.0)

    # instance 2: bottom-right cell (512, 0, 1024, 1024) ->
    # fitted square (512, 256, 1024, 768).
    p2_lo = apply_affine_to_point(resolved[2].transform, (0.0, 0.0))
    p2_hi = apply_affine_to_point(resolved[2].transform, (1024.0, 1024.0))
    assert p2_lo == (512.0, 256.0)
    assert p2_hi == (1024.0, 768.0)


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
