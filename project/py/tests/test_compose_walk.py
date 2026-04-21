from pathlib import Path

from olik_font.compose.walk import compose_transforms
from olik_font.decompose.instance import build_instance_tree
from olik_font.geom import apply_affine_to_point
from olik_font.prototypes.extraction_plan import load_extraction_plan
from olik_font.types import Affine

PLAN = Path(__file__).resolve().parents[1] / "data" / "extraction_plan.yaml"


def test_ming_root_left_right_resolves_child_transforms():
    plan = load_extraction_plan(PLAN)
    tree = build_instance_tree("明", plan)
    resolved, _ = compose_transforms(tree, glyph_bbox=(0, 0, 1024, 1024))

    left, right = resolved.children
    # left should occupy upper-left quadrant of glyph space
    assert apply_affine_to_point(left.transform, (0, 0)) == (0.0, 0.0)
    # right should start after the split + gap
    rx0, _ = apply_affine_to_point(right.transform, (0, 0))
    assert rx0 > 400  # split at 40% = 409.6 + gap -> ~420


def test_qing_recursive_resolves_depth_2_children():
    plan = load_extraction_plan(PLAN)
    tree = build_instance_tree("清", plan)
    resolved, _ = compose_transforms(tree, glyph_bbox=(0, 0, 1024, 1024))

    water, qing = resolved.children
    assert water.transform != Affine.identity()
    assert qing.transform != Affine.identity()
    # qing is refined -> its children should also have transforms
    sheng, moon = qing.children
    assert sheng.transform != Affine.identity()
    assert moon.transform != Affine.identity()
    # sheng's placed position should be within qing's placed bbox's upper half
    sheng_origin = apply_affine_to_point(sheng.transform, (0, 0))
    qing_origin = apply_affine_to_point(qing.transform, (0, 0))
    assert sheng_origin[0] >= qing_origin[0] - 1  # horizontal within qing
    assert sheng_origin[1] >= qing_origin[1] - 1  # starts at qing's top


def test_guo_enclose_resolves():
    plan = load_extraction_plan(PLAN)
    tree = build_instance_tree("國", plan)
    resolved, _ = compose_transforms(tree, glyph_bbox=(0, 0, 1024, 1024))
    outer, inner = resolved.children
    assert apply_affine_to_point(outer.transform, (0, 0)) == (0.0, 0.0)
    # inner should be padded inside outer
    inner_origin = apply_affine_to_point(inner.transform, (0, 0))
    assert 80 < inner_origin[0] < 140


def test_senr_repeat_triangle_resolves():
    plan = load_extraction_plan(PLAN)
    tree = build_instance_tree("森", plan)
    resolved, _ = compose_transforms(tree, glyph_bbox=(0, 0, 1024, 1024))
    assert len(resolved.children) == 3
    centers = [apply_affine_to_point(c.transform, (512, 512)) for c in resolved.children]
    ys = sorted(c[1] for c in centers)
    assert ys[0] < 400  # one near top
    assert ys[1] > 500 and ys[2] > 500  # two near bottom
