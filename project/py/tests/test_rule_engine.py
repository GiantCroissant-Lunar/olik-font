from pathlib import Path

from olik_font.rules.engine import (
    RuleSet,
    RuleTrace,
    apply_first_match,
    load_rules,
)

RULES = Path(__file__).resolve().parents[1] / "src" / "olik_font" / "rules" / "rules.yaml"


def test_load_rules_returns_three_buckets():
    rs = load_rules(RULES)
    assert isinstance(rs, RuleSet)
    assert len(rs.decomposition) == 2
    assert len(rs.composition) == 3
    assert len(rs.prototype_extraction) == 2


def test_apply_first_match_picks_first_applicable_rule():
    rs = load_rules(RULES)
    trace = apply_first_match(
        bucket=rs.composition,
        inputs={"has_preset_in_plan": True, "preset": "left_right"},
        decision_id="d:test",
    )
    assert isinstance(trace, RuleTrace)
    assert trace.rule_id == "compose.preset_from_plan"
    assert trace.output == {"adapter": "preset"}


def test_apply_first_match_records_alternatives():
    rs = load_rules(RULES)
    trace = apply_first_match(
        bucket=rs.composition,
        inputs={"preset": "repeat_triangle", "has_preset_in_plan": True},
        decision_id="d:test",
    )
    # both preset_from_plan AND direct_for_repeat_triangle would match. First wins,
    # remaining applicable rules show up as alternatives.
    assert trace.rule_id == "compose.preset_from_plan"
    alt_ids = {alt.rule_id for alt in trace.alternatives}
    assert "compose.direct_for_repeat_triangle" in alt_ids


def test_fallback_rule_when_nothing_else_matches():
    rs = load_rules(RULES)
    trace = apply_first_match(
        bucket=rs.composition,
        inputs={},
        decision_id="d:test",
    )
    assert trace.rule_id == "compose.default_identity"
