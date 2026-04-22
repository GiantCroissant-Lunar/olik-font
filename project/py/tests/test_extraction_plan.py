from pathlib import Path

import pytest

from olik_font.prototypes.extraction_plan import (
    ExtractionPlan,
    GlyphPlan,
    PrototypePlan,
    load_extraction_plan,
)

PLAN = Path(__file__).resolve().parents[1] / "data" / "extraction_plan.yaml"


def test_load_returns_typed_plan():
    plan = load_extraction_plan(PLAN)
    assert isinstance(plan, ExtractionPlan)
    assert plan.schema_version == "0.1"


def test_plan_has_nine_prototypes():
    plan = load_extraction_plan(PLAN)
    assert len(plan.prototypes) == 9
    ids = {p.id for p in plan.prototypes}
    assert "proto:sun" in ids and "proto:tree" in ids
    assert "proto:sheng_in_qing" in ids and "proto:moon_in_qing" in ids


def test_prototype_plan_keeps_stroke_indices_as_tuple():
    plan = load_extraction_plan(PLAN)
    sun = plan.by_prototype_id["proto:sun"]
    assert isinstance(sun, PrototypePlan)
    assert sun.stroke_indices == (0, 1, 2, 3)
    assert sun.from_char == "明"


def test_glyph_plan_for_senr_expands_to_three_tree_children():
    plan = load_extraction_plan(PLAN)
    senr = plan.glyphs["森"]
    assert isinstance(senr, GlyphPlan)
    assert len(senr.children) == 3
    assert {child.prototype_ref for child in senr.children} == {"proto:tree"}


def test_glyph_plan_refine_node_carries_children():
    plan = load_extraction_plan(PLAN)
    qing = plan.glyphs["清"]
    # root → [氵, 青]; 青 has mode=refine + its own children
    assert len(qing.children) == 2
    right = qing.children[1]
    assert right.mode == "refine"
    assert right.source_stroke_indices is None
    assert len(right.children) == 2


def test_invalid_yaml_raises():
    with pytest.raises(ValueError):
        load_extraction_plan(Path("/nonexistent"))
