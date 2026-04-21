"""Ordered, named rule engine with trace recording.

Rules are declarative (data in YAML). Matching is shallow: a rule's `when`
clause is a dict; the rule matches if every (key, value) in `when` is
present (and equal) in the inputs. Empty `when` is the always-match fallback.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True, slots=True)
class Rule:
    id: str
    when: dict[str, Any]
    action: dict[str, Any]


@dataclass(frozen=True, slots=True)
class RuleSet:
    schema_version: str
    decomposition: tuple[Rule, ...]
    composition: tuple[Rule, ...]
    prototype_extraction: tuple[Rule, ...]


@dataclass(frozen=True, slots=True)
class RuleTraceAlternative:
    rule_id: str
    would_output: dict[str, Any]


@dataclass(frozen=True, slots=True)
class RuleTrace:
    decision_id: str
    rule_id: str
    inputs: dict[str, Any]
    output: dict[str, Any]
    alternatives: tuple[RuleTraceAlternative, ...] = ()
    applied_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


def load_rules(path: Path) -> RuleSet:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return RuleSet(
        schema_version=raw["schema_version"],
        decomposition=tuple(_parse_rule(r) for r in raw.get("decomposition", [])),
        composition=tuple(_parse_rule(r) for r in raw.get("composition", [])),
        prototype_extraction=tuple(_parse_rule(r) for r in raw.get("prototype_extraction", [])),
    )


def _parse_rule(obj: dict) -> Rule:
    return Rule(
        id=obj["id"], when=dict(obj.get("when") or {}), action=dict(obj.get("action") or {})
    )


def _matches(rule: Rule, inputs: dict[str, Any]) -> bool:
    for key, expected in rule.when.items():
        if key not in inputs or inputs[key] != expected:
            return False
    return True


def apply_first_match(
    bucket: tuple[Rule, ...] | list[Rule],
    inputs: dict[str, Any],
    decision_id: str,
) -> RuleTrace:
    winner: Rule | None = None
    alternatives: list[RuleTraceAlternative] = []
    for r in bucket:
        if _matches(r, inputs):
            if winner is None:
                winner = r
            else:
                alternatives.append(RuleTraceAlternative(rule_id=r.id, would_output=dict(r.action)))
    if winner is None:
        raise ValueError(f"no rule matched inputs={inputs}")
    return RuleTrace(
        decision_id=decision_id,
        rule_id=winner.id,
        inputs=dict(inputs),
        output=dict(winner.action),
        alternatives=tuple(alternatives),
    )
