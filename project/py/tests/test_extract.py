from pathlib import Path

import pytest

from olik_font.prototypes.extract import extract_all_prototypes, extract_prototype
from olik_font.prototypes.extraction_plan import load_extraction_plan
from olik_font.sources.makemeahanzi import load_mmh_graphics
from olik_font.types import Prototype, PrototypeLibrary

ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "data" / "extraction_plan.yaml"
MMH = ROOT / "data" / "mmh" / "graphics.txt"

pytestmark = pytest.mark.skipif(not MMH.exists(), reason="run Plan 01 Task 4 first")


def test_extract_single_prototype_produces_canonical_1024_bbox():
    plan = load_extraction_plan(PLAN)
    chars = load_mmh_graphics(MMH)
    sun_plan = plan.by_prototype_id["proto:sun"]

    proto = extract_prototype(sun_plan, chars[sun_plan.from_char])
    assert isinstance(proto, Prototype)
    assert proto.id == "proto:sun"
    assert proto.canonical_bbox == (0.0, 0.0, 1024.0, 1024.0)
    assert len(proto.strokes) == 4
    # anchors come from the plan, not derived
    assert "center" in proto.anchors


def test_extract_all_populates_library():
    plan = load_extraction_plan(PLAN)
    chars = load_mmh_graphics(MMH)

    lib = PrototypeLibrary()
    extract_all_prototypes(plan, chars, lib)

    assert len(lib) == 9
    assert lib.contains("proto:sun")
    assert lib.contains("proto:tree")
    assert lib.contains("proto:sheng_in_qing")
    assert lib.contains("proto:moon_in_qing")


def test_missing_char_raises():
    plan = load_extraction_plan(PLAN)
    with pytest.raises(KeyError):
        extract_prototype(plan.by_prototype_id["proto:sun"], None)  # type: ignore[arg-type]
