"""Prototype reuse decision + context-variant fallback.

The decision layer takes a MEASURED slot bbox (computed by the planner
from MMH's `matches` field), not a preset label. The probe closure
signature is `(component_char, context_char, slot) -> float`.
"""

from __future__ import annotations

from olik_font.bulk.reuse import (
    ProtoIndex,
    canonical_id,
    decide_prototype,
    variant_id,
)
from olik_font.prototypes.extraction_plan import PrototypePlan

_SLOT = (0.0, 0.0, 512.0, 1024.0)


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
    assert canonical_id("木") == "proto:u6728"
    assert canonical_id("日") == "proto:u65e5"


def test_variant_id_includes_context() -> None:
    assert variant_id("木", "林") == "proto:u6728_in_林"


def test_reuse_when_canonical_exists() -> None:
    cid = canonical_id("木")
    idx = ProtoIndex(prototypes=[_proto(cid, "木", "木", (0, 1, 2, 3))])
    decision = decide_prototype(
        component_char="木",
        context_char="林",
        slot=_SLOT,
        index=idx,
        probe_iou=lambda *_a, **_kw: 1.0,
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
        slot=_SLOT,
        index=idx,
        probe_iou=lambda *_a, **_kw: 1.0,
        gate=0.90,
        cap=2,
    )
    assert decision.chosen_id == canonical_id("木")
    assert decision.is_new_canonical is True


def test_hand_tuned_seed_prototypes_are_not_reused() -> None:
    seed = _proto("proto:sun", "日", "明", (0, 1, 2, 3))
    idx = ProtoIndex(prototypes=[seed])
    decision = decide_prototype(
        component_char="日",
        context_char="旭",
        slot=_SLOT,
        index=idx,
        probe_iou=lambda *_a, **_kw: 1.0,
        gate=0.90,
        cap=2,
    )
    assert decision.chosen_id == canonical_id("日")
    assert decision.is_new_canonical is True


def test_variant_decision_fires_when_canonical_below_gate() -> None:
    cid = canonical_id("木")
    idx = ProtoIndex(prototypes=[_proto(cid, "木", "木", (0, 1, 2, 3))])
    decision = decide_prototype(
        component_char="木",
        context_char="林",
        slot=_SLOT,
        index=idx,
        probe_iou=lambda *_a, **_kw: 0.7,
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
        slot=_SLOT,
        index=idx,
        probe_iou=lambda *_a, **_kw: 0.7,
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
        slot=_SLOT,
        index=idx,
        probe_iou=lambda *_a, **_kw: 0.5,
        gate=0.90,
        cap=2,
    )
    assert decision.chosen_id is None
    assert decision.cap_exceeded is True


def test_probe_iou_receives_measured_slot() -> None:
    """Probe signature: (component_char, context_char, slot) -> float."""
    cid = canonical_id("木")
    idx = ProtoIndex(prototypes=[_proto(cid, "木", "木", (0, 1, 2, 3))])
    received: dict[str, object] = {}

    def spy_probe(comp: str, ctx: str, slot):
        received.update(comp=comp, ctx=ctx, slot=slot)
        return 1.0

    decide_prototype(
        component_char="木",
        context_char="林",
        slot=_SLOT,
        index=idx,
        probe_iou=spy_probe,
        gate=0.90,
        cap=2,
    )
    assert received == {"comp": "木", "ctx": "林", "slot": _SLOT}
