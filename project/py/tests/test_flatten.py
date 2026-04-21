from pathlib import Path

import pytest

from olik_font.compose.flatten import flatten_strokes
from olik_font.compose.walk import compose_transforms
from olik_font.decompose.instance import build_instance_tree
from olik_font.prototypes.extract import extract_all_prototypes
from olik_font.prototypes.extraction_plan import load_extraction_plan
from olik_font.sources.makemeahanzi import load_mmh_graphics
from olik_font.types import PrototypeLibrary

ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "data" / "extraction_plan.yaml"
MMH = ROOT / "data" / "mmh" / "graphics.txt"

pytestmark = pytest.mark.skipif(not MMH.exists(), reason="run Plan 01 Task 4 first")


@pytest.fixture(scope="module")
def lib_and_plan():
    plan = load_extraction_plan(PLAN)
    chars = load_mmh_graphics(MMH)
    lib = PrototypeLibrary()
    extract_all_prototypes(plan, chars, lib)
    return lib, plan


def test_ming_flattens_to_eight_stroke_instances(lib_and_plan):
    lib, plan = lib_and_plan
    tree = build_instance_tree("明", plan)
    resolved, _ = compose_transforms(tree, glyph_bbox=(0, 0, 1024, 1024))
    strokes = flatten_strokes(resolved, lib)
    assert len(strokes) == 8  # 4 from 日 + 4 from 月
    # every stroke has instance_id linking back to a leaf
    assert all(s.instance_id.startswith("inst:") for s in strokes)
    assert all(0 <= s.z <= 99 for s in strokes)


def test_senr_flattens_to_twelve_from_same_prototype(lib_and_plan):
    lib, plan = lib_and_plan
    tree = build_instance_tree("森", plan)
    resolved, _ = compose_transforms(tree, glyph_bbox=(0, 0, 1024, 1024))
    strokes = flatten_strokes(resolved, lib)
    assert len(strokes) == 12  # 4 strokes x 3 木 instances
    instance_ids = {s.instance_id for s in strokes}
    assert len(instance_ids) == 3


def test_qing_skips_refine_intermediate(lib_and_plan):
    lib, plan = lib_and_plan
    tree = build_instance_tree("清", plan)
    resolved, _ = compose_transforms(tree, glyph_bbox=(0, 0, 1024, 1024))
    strokes = flatten_strokes(resolved, lib)
    # 氵 (3) + 生 (5) + 月 (4) = 12. The refine-intermediate 青 has no own strokes.
    assert len(strokes) == 12
    refs = {s.instance_id.split("_")[0] for s in strokes}
    # at least three distinct source instances (氵, 生, 月)
    assert len(refs) >= 3
