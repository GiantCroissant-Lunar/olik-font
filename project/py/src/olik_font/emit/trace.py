"""Serialize RuleTrace records to JSON-ready dicts."""

from __future__ import annotations

from olik_font.rules.engine import RuleTrace


def trace_to_dict(t: RuleTrace) -> dict:
    return {
        "decision_id": t.decision_id,
        "rule_id": t.rule_id,
        "inputs": dict(t.inputs),
        "output": dict(t.output),
        "alternatives": [
            {"rule_id": alt.rule_id, "would_output": dict(alt.would_output)}
            for alt in t.alternatives
        ],
        "applied_at": t.applied_at,
    }
