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
    assert len(rs.composition) == 2
    assert len(rs.prototype_extraction) == 2


def test_apply_first_match_picks_first_applicable_rule():
    rs = load_rules(RULES)
    trace = apply_first_match(
        bucket=rs.composition,
        inputs={"compose_source": "measured_transforms"},
        decision_id="d:test",
    )
    assert isinstance(trace, RuleTrace)
    assert trace.rule_id == "compose.measured_transforms"
    assert trace.output == {"adapter": "measured"}


def test_apply_first_match_records_alternatives():
    rs = load_rules(RULES)
    trace = apply_first_match(
        bucket=rs.composition,
        inputs={"compose_source": "measured_transforms"},
        decision_id="d:test",
    )
    # compose.default_identity is always applicable (when: {}) — it
    # shows up in the alternatives list after the first match fires.
    alt_ids = {alt.rule_id for alt in trace.alternatives}
    assert "compose.default_identity" in alt_ids


def test_fallback_rule_when_nothing_else_matches():
    rs = load_rules(RULES)
    trace = apply_first_match(
        bucket=rs.composition,
        inputs={},
        decision_id="d:test",
    )
    assert trace.rule_id == "compose.default_identity"
