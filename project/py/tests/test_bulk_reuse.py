"""Prototype reuse decision + context-variant fallback.

Plan 09.1: name_to_slug produces `u<hex>` slugs uniformly. The hand-tuned
seed prototypes (proto:sun, proto:moon, ...) are intentionally NOT
reused by the auto-planner — they were extracted from context chars
rather than standalone MMH entries, which is the bug Plan 09.1 fixes.
Auto-planned prototypes use `proto:u<hex>` IDs so the two systems stay
disjoint in the DB.
"""

from __future__ import annotations

from olik_font.bulk.reuse import (
    ProtoIndex,
    canonical_id,
    decide_prototype,
    variant_id,
)
from olik_font.prototypes.extraction_plan import PrototypePlan


def _proto(id_: str, name: str, from_char: str, strokes: tuple[int, ...]) -> PrototypePlan:
    return PrototypePlan(
        id=id_,
        name=name,
        from_char=from_char,
        stroke_indices=strokes,
        roles=("meaning",),
        anchors={},
    )


def test_canonical_id_uses_codepoint_slug() -> None:
    # 木 = U+6728 → u6728
    assert canonical_id("木") == "proto:u6728"
    # 日 = U+65E5 → u65e5 (no longer maps to the seed's proto:sun)
    assert canonical_id("日") == "proto:u65e5"


def test_variant_id_includes_context() -> None:
    assert variant_id("木", "林") == "proto:u6728_in_林"


def test_reuse_when_canonical_exists() -> None:
    cid = canonical_id("木")
    idx = ProtoIndex(prototypes=[_proto(cid, "木", "木", (0, 1, 2, 3))])
    decision = decide_prototype(
        component_char="木",
        context_char="林",
        index=idx,
        probe_iou=lambda _: 1.0,
        gate=0.90,
        cap=2,
    )
    assert decision.chosen_id == cid
    assert decision.canonical_for_edge is None
    assert decision.is_new_variant is False


def test_new_prototype_when_none_exists() -> None:
    idx = ProtoIndex(prototypes=[])
    decision = decide_prototype(
        component_char="木",
        context_char="林",
        index=idx,
        probe_iou=lambda _: 1.0,
        gate=0.90,
        cap=2,
    )
    assert decision.chosen_id == canonical_id("木")
    assert decision.is_new_canonical is True


def test_hand_tuned_seed_prototypes_are_not_reused() -> None:
    """Seed rows like proto:sun (minted from 明's strokes 0..3) must
    NOT be picked up by the auto-planner — their from_char is wrong.
    Auto-planner looks up `canonical_id('日')` = `proto:u65e5`, which
    the seed row does not satisfy.
    """
    seed = _proto("proto:sun", "日", "明", (0, 1, 2, 3))
    idx = ProtoIndex(prototypes=[seed])
    decision = decide_prototype(
        component_char="日",
        context_char="旭",
        index=idx,
        probe_iou=lambda _: 1.0,
        gate=0.90,
        cap=2,
    )
    # Must treat as new canonical (minted from 日's own MMH entry).
    assert decision.chosen_id == canonical_id("日")
    assert decision.is_new_canonical is True


def test_variant_decision_fires_when_canonical_below_gate() -> None:
    """The decision layer still proposes a variant when canonical IoU
    fails. Plan 09.1's planner chooses NOT to mint it (returns
    PlanFailed instead) — that choice is tested in test_bulk_planner."""
    cid = canonical_id("木")
    idx = ProtoIndex(prototypes=[_proto(cid, "木", "木", (0, 1, 2, 3))])
    decision = decide_prototype(
        component_char="木",
        context_char="林",
        index=idx,
        probe_iou=lambda _: 0.7,
        gate=0.90,
        cap=2,
    )
    assert decision.chosen_id == variant_id("木", "林")
    assert decision.canonical_for_edge == cid
    assert decision.is_new_variant is True


def test_variant_reuse_when_context_match_exists() -> None:
    cid = canonical_id("木")
    vid = variant_id("木", "林")
    idx = ProtoIndex(
        prototypes=[
            _proto(cid, "木", "木", (0, 1, 2, 3)),
            _proto(vid, "木", "林", (0, 1, 2, 3)),
        ]
    )
    decision = decide_prototype(
        component_char="木",
        context_char="林",
        index=idx,
        probe_iou=lambda _: 0.7,
        gate=0.90,
        cap=2,
    )
    assert decision.chosen_id == vid
    assert decision.canonical_for_edge is None
    assert decision.is_new_variant is False


def test_variant_cap_exceeded_signals_review() -> None:
    cid = canonical_id("木")
    idx = ProtoIndex(
        prototypes=[
            _proto(cid, "木", "木", (0, 1, 2, 3)),
            _proto(variant_id("木", "桂"), "木", "桂", (0, 1, 2, 3)),
            _proto(variant_id("木", "松"), "木", "松", (0, 1, 2, 3)),
        ]
    )
    decision = decide_prototype(
        component_char="木",
        context_char="橋",
        index=idx,
        probe_iou=lambda _: 0.5,
        gate=0.90,
        cap=2,
    )
    assert decision.chosen_id is None
    assert decision.cap_exceeded is True
