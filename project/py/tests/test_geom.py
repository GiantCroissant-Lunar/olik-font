import math

from olik_font.geom import (
    affine_compose,
    apply_affine_to_median,
    apply_affine_to_point,
    bbox_of_paths,
    bbox_to_bbox_affine,
    normalize_paths_to_canonical,
    union_bbox,
)
from olik_font.types import Affine


def test_apply_identity_is_noop():
    assert apply_affine_to_point(Affine.identity(), (3.0, 4.0)) == (3.0, 4.0)


def test_apply_translate_and_scale():
    a = Affine(translate=(10.0, 20.0), scale=(2.0, 3.0))
    assert apply_affine_to_point(a, (1.0, 2.0)) == (12.0, 26.0)


def test_apply_rotation_90_deg():
    a = Affine(rotate=math.pi / 2.0)
    x, y = apply_affine_to_point(a, (1.0, 0.0))
    assert math.isclose(x, 0.0, abs_tol=1e-9)
    assert math.isclose(y, 1.0, abs_tol=1e-9)


def test_compose_is_left_applied_first():
    a = Affine(translate=(10.0, 0.0))
    b = Affine(scale=(2.0, 1.0))
    composed = affine_compose(b, a)  # apply a then b
    # point (1,0): a → (11,0), b → (22,0)
    assert apply_affine_to_point(composed, (1.0, 0.0)) == (22.0, 0.0)


def test_bbox_of_paths_simple_line():
    bbox = bbox_of_paths(["M 10 20 L 30 50"])
    assert bbox == (10.0, 20.0, 30.0, 50.0)


def test_union_bbox():
    assert union_bbox(((0, 0, 10, 10), (5, 5, 20, 30))) == (0.0, 0.0, 20.0, 30.0)


def test_bbox_to_bbox_affine_maps_corners():
    src = (100.0, 200.0, 300.0, 400.0)
    dst = (0.0, 0.0, 1024.0, 1024.0)
    a = bbox_to_bbox_affine(src, dst)
    assert apply_affine_to_point(a, (100.0, 200.0)) == (0.0, 0.0)
    assert apply_affine_to_point(a, (300.0, 400.0)) == (1024.0, 1024.0)


def test_normalize_paths_to_canonical_preserves_move_to():
    paths = ["M 100 200 L 300 400"]
    normalized, fwd = normalize_paths_to_canonical(paths, (0.0, 0.0, 1024.0, 1024.0))
    assert normalized[0].startswith("M ")
    p0 = apply_affine_to_point(fwd, (100.0, 200.0))
    assert p0 == (0.0, 0.0)


def test_apply_affine_to_median_scales_points():
    a = Affine(scale=(2.0, 3.0))
    med = apply_affine_to_median(a, ((1.0, 1.0), (2.0, 2.0)))
    assert med == ((2.0, 3.0), (4.0, 6.0))
