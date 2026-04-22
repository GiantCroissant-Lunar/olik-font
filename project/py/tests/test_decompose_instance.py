from pathlib import Path

from olik_font.decompose.instance import build_instance_tree
from olik_font.prototypes.extraction_plan import load_extraction_plan
from olik_font.types import InstancePlacement

PLAN = Path(__file__).resolve().parents[1] / "data" / "extraction_plan.yaml"


def test_ming_builds_flat_two_leaves():
    plan = load_extraction_plan(PLAN)
    root = build_instance_tree("明", plan)
    assert isinstance(root, InstancePlacement)
    assert root.input_adapter == "extraction_plan"
    assert len(root.children) == 2
    assert root.children[0].prototype_ref == "proto:sun"
    assert root.children[1].prototype_ref == "proto:moon"
    # compose resolves placement; build step only carries source geometry inputs
    assert root.children[0].transform is None
    assert root.children[0].source_stroke_indices == (0, 1, 2, 3)
    assert root.children[0].input_adapter == "measured"


def test_qing_refines_to_depth_2():
    plan = load_extraction_plan(PLAN)
    root = build_instance_tree("清", plan)
    assert len(root.children) == 2
    water, qing = root.children
    assert water.prototype_ref == "proto:water_3dots"
    assert water.source_stroke_indices == (0, 1, 2)
    assert qing.mode == "refine"
    assert qing.input_adapter == "refine"
    assert len(qing.children) == 2
    assert qing.children[0].prototype_ref == "proto:sheng_in_qing"
    assert qing.children[1].prototype_ref == "proto:moon_in_qing"
    assert qing.children[0].source_stroke_indices == (3, 4, 5, 6)
    assert qing.children[1].source_stroke_indices == (7, 8, 9, 10)
    # depths
    assert water.depth == 1
    assert qing.depth == 1
    assert qing.children[0].depth == 2


def test_senr_creates_three_tree_instances_from_one_prototype():
    plan = load_extraction_plan(PLAN)
    root = build_instance_tree("森", plan)
    assert root.input_adapter == "extraction_plan"
    assert len(root.children) == 3
    for child in root.children:
        assert child.prototype_ref == "proto:tree"
    # each child has a unique instance_id
    ids = {c.instance_id for c in root.children}
    assert len(ids) == 3
    assert [child.source_stroke_indices for child in root.children] == [
        (0, 1, 2, 3),
        (4, 5, 6, 7),
        (8, 9, 10, 11),
    ]


def test_guo_enclose_has_two_leaves():
    plan = load_extraction_plan(PLAN)
    root = build_instance_tree("國", plan)
    assert root.input_adapter == "extraction_plan"
    assert len(root.children) == 2
    assert root.children[0].prototype_ref == "proto:enclosure_box"
    assert root.children[1].prototype_ref == "proto:huo"
    assert root.children[0].source_stroke_indices == (0, 1, 10)
    assert root.children[1].source_stroke_indices == (2, 3, 4, 5, 6, 7, 8, 9)
