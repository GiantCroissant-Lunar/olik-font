import json
from pathlib import Path

import jsonschema
import pytest

from olik_font.compose.walk import compose_transforms
from olik_font.decompose.instance import build_instance_tree
from olik_font.emit.library import library_to_dict
from olik_font.emit.record import build_glyph_record
from olik_font.emit.trace import trace_to_dict
from olik_font.prototypes.extract import extract_all_prototypes
from olik_font.prototypes.extraction_plan import load_extraction_plan
from olik_font.rules.engine import RuleTrace
from olik_font.sources.makemeahanzi import load_mmh_graphics
from olik_font.types import PrototypeLibrary

ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "data" / "extraction_plan.yaml"
MMH = ROOT / "data" / "mmh" / "graphics.txt"
SCHEMA_ROOT = ROOT.parent / "schema"

pytestmark = pytest.mark.skipif(not MMH.exists(), reason="run Plan 01 Task 4 first")


def _lib_schema():
    return json.loads((SCHEMA_ROOT / "prototype-library.schema.json").read_text())


def _record_schema():
    return json.loads((SCHEMA_ROOT / "glyph-record.schema.json").read_text())


@pytest.fixture(scope="module")
def lib_and_plan():
    plan = load_extraction_plan(PLAN)
    chars = load_mmh_graphics(MMH)
    lib = PrototypeLibrary()
    extract_all_prototypes(plan, chars, lib)
    return lib, plan, chars


def test_library_json_validates(lib_and_plan):
    lib, _, _ = lib_and_plan
    d = library_to_dict(lib)
    jsonschema.Draft202012Validator(_lib_schema()).validate(d)


def test_ming_record_validates_and_has_8_strokes(lib_and_plan):
    lib, plan, chars = lib_and_plan
    tree = build_instance_tree("明", plan)
    resolved, cs = compose_transforms(tree, glyph_bbox=(0, 0, 1024, 1024))
    record = build_glyph_record("明", resolved, cs, lib, mmh_char=chars["明"])
    jsonschema.Draft202012Validator(_record_schema()).validate(record)
    assert record["glyph_id"] == "明"
    assert len(record["stroke_instances"]) == 8
    assert len(record["constraints"]) >= 3


def test_record_carries_iou_report(lib_and_plan):
    lib, plan, chars = lib_and_plan
    tree = build_instance_tree("明", plan)
    resolved, cs = compose_transforms(tree, glyph_bbox=(0, 0, 1024, 1024))
    record = build_glyph_record("明", resolved, cs, lib, mmh_char=chars["明"])
    iou = record["metadata"]["iou_report"]
    assert "mean" in iou and "min" in iou and "per_stroke" in iou


def test_trace_to_dict_shape():
    tr = RuleTrace(
        decision_id="d:test",
        rule_id="x",
        inputs={"a": 1},
        output={"b": 2},
    )
    d = trace_to_dict(tr)
    assert d["rule_id"] == "x"
    assert d["inputs"] == {"a": 1}
    assert d["output"] == {"b": 2}
    assert "applied_at" in d
    assert d["alternatives"] == []
