from pathlib import Path

from olik_font.prototypes.extraction_plan import GlyphNodePlan, GlyphPlan, load_extraction_plan

PLAN = Path(__file__).resolve().parents[1] / "data" / "extraction_plan.yaml"


def test_parsed_glyph_plans_do_not_expose_preset_attribute():
    plan = load_extraction_plan(PLAN)

    def walk(node: GlyphNodePlan) -> tuple[GlyphNodePlan, ...]:
        return (node, *tuple(grandchild for child in node.children for grandchild in walk(child)))

    for glyph_plan in plan.glyphs.values():
        assert isinstance(glyph_plan, GlyphPlan)
        assert not hasattr(glyph_plan, "preset")
        for child in glyph_plan.children:
            for node in walk(child):
                assert not hasattr(node, "preset")


def test_shipped_plan_yaml_contains_no_preset_keys():
    assert "preset:" not in PLAN.read_text(encoding="utf-8")
