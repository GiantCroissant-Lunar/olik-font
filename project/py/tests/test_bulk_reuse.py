"""Prototype reuse decision + context-variant fallback."""

from __future__ import annotations

from olik_font.bulk.reuse import ProtoIndex, decide_prototype
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


def test_reuse_when_canonical_exists() -> None:
    idx = ProtoIndex(prototypes=[_proto("proto:tree", "木", "森", (0, 1, 2, 3))])
    decision = decide_prototype(
        component_char="木",
        context_char="林",
        index=idx,
        probe_iou=lambda _: 1.0,
        gate=0.90,
        cap=2,
    )
    assert decision.chosen_id == "proto:tree"
    assert decision.canonical_for_edge is None
    assert decision.is_new_variant is False


def test_variant_created_when_canonical_below_gate() -> None:
    idx = ProtoIndex(prototypes=[_proto("proto:tree", "木", "森", (0, 1, 2, 3))])
    decision = decide_prototype(
        component_char="木",
        context_char="林",
        index=idx,
        probe_iou=lambda _: 0.7,
        gate=0.90,
        cap=2,
    )
    assert decision.chosen_id == "proto:tree_in_林"
    assert decision.canonical_for_edge == "proto:tree"
    assert decision.is_new_variant is True


def test_variant_reuse_when_context_match_exists() -> None:
    idx = ProtoIndex(
        prototypes=[
            _proto("proto:tree", "木", "森", (0, 1, 2, 3)),
            _proto("proto:tree_in_林", "木", "林", (0, 1, 2, 3)),
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
    assert decision.chosen_id == "proto:tree_in_林"
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
    assert decision.chosen_id == "proto:tree"
    assert decision.is_new_canonical is True


def test_variant_cap_exceeded_signals_review() -> None:
    idx = ProtoIndex(
        prototypes=[
            _proto("proto:tree", "木", "森", (0, 1, 2, 3)),
            _proto("proto:tree_in_桂", "木", "桂", (0, 1, 2, 3)),
            _proto("proto:tree_in_松", "木", "松", (0, 1, 2, 3)),
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
