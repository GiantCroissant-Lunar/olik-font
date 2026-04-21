from pathlib import Path

import pytest

from olik_font.decompose.instance import build_instance_tree
from olik_font.prototypes.extract import extract_all_prototypes
from olik_font.prototypes.extraction_plan import load_extraction_plan
from olik_font.sources.makemeahanzi import load_mmh_graphics
from olik_font.types import PrototypeLibrary

ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = ROOT / "data" / "extraction_plan.yaml"
MMH = ROOT / "data" / "mmh" / "graphics.txt"

pytestmark = pytest.mark.skipif(not MMH.exists(), reason="run Plan 01 Task 4 first")

SEED = ["明", "清", "國", "森"]


@pytest.fixture(scope="module")
def lib_and_plan():
    plan = load_extraction_plan(PLAN_PATH)
    chars = load_mmh_graphics(MMH)
    lib = PrototypeLibrary()
    extract_all_prototypes(plan, chars, lib)
    return lib, plan


def test_all_seed_chars_build_instance_trees(lib_and_plan):
    _, plan = lib_and_plan
    for ch in SEED:
        tree = build_instance_tree(ch, plan)
        assert tree.instance_id.startswith("inst:")
        assert len(tree.children) in (2, 3)


def test_prototype_library_has_expected_nine(lib_and_plan):
    lib, _ = lib_and_plan
    expected = {
        "proto:sun",
        "proto:moon",
        "proto:water_3dots",
        "proto:sheng",
        "proto:sheng_in_qing",
        "proto:moon_in_qing",
        "proto:enclosure_box",
        "proto:huo",
        "proto:tree",
    }
    assert set(lib.ids()) == expected


def test_qing_tree_refines(lib_and_plan):
    _, plan = lib_and_plan
    tree = build_instance_tree("清", plan)
    right = tree.children[1]
    assert right.mode == "refine"
    leaf_refs = {c.prototype_ref for c in right.children}
    assert leaf_refs == {"proto:sheng_in_qing", "proto:moon_in_qing"}


def test_senr_has_three_leaves_of_same_prototype(lib_and_plan):
    _, plan = lib_and_plan
    tree = build_instance_tree("森", plan)
    assert len({c.prototype_ref for c in tree.children}) == 1
    assert {c.instance_id for c in tree.children} | {tree.instance_id} == {
        tree.instance_id,
        *(c.instance_id for c in tree.children),
    }
    assert len({c.instance_id for c in tree.children}) == 3
