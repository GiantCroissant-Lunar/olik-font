"""plan_char — auto-build ExtractionPlan fragments from cjk-decomp."""

from __future__ import annotations

from olik_font.bulk.planner import (
    PlanFailed,
    PlanOk,
    PlanUnsupported,
    plan_char,
)
from olik_font.bulk.reuse import ProtoIndex, canonical_id, variant_id
from olik_font.prototypes.extraction_plan import PrototypePlan


def _rect_path(x0: float, y0: float, x1: float, y1: float) -> str:
    return f"M{x0},{y0} L{x1},{y0} L{x1},{y1} L{x0},{y1} Z"


# Canonicals are extracted from the component's own standalone MMH entry
# (Plan 09.1 fix), so every component of a char-under-test must have an
# entry in MINIMAL_MMH.
MINIMAL_MMH = {
    "明": {
        "character": "明",
        "strokes": ["M0", "M1", "M2", "M3", "M4", "M5", "M6", "M7"],
        "medians": [[]] * 8,
    },
    "日": {"character": "日", "strokes": ["D0", "D1", "D2", "D3"], "medians": [[]] * 4},
    "月": {"character": "月", "strokes": ["Y0", "Y1", "Y2", "Y3"], "medians": [[]] * 4},
}


def test_plan_char_supported_op_returns_ok() -> None:
    result = plan_char(
        char="明",
        cjk_entry={"operator": "a", "components": ["日", "月"]},
        mmh=MINIMAL_MMH,
        index=ProtoIndex(prototypes=[]),
        probe_iou=lambda *_a, **_kw: 1.0,
        gate=0.90,
        cap=2,
    )
    assert isinstance(result, PlanOk)
    assert result.glyph_plan.preset == "left_right"
    assert len(result.glyph_plan.children) == 2
    assert {p.id for p in result.new_prototypes} == {
        canonical_id("日"),
        canonical_id("月"),
    }
    by_name = {p.name: p for p in result.new_prototypes}
    assert by_name["日"].stroke_indices == (0, 1, 2, 3)
    assert by_name["日"].from_char == "日"
    assert by_name["月"].stroke_indices == (0, 1, 2, 3)
    assert by_name["月"].from_char == "月"


def test_plan_char_unsupported_op_returns_sentinel() -> None:
    result = plan_char(
        char="彌",
        cjk_entry={"operator": "wb", "components": ["弓", "爾"]},
        mmh=MINIMAL_MMH,
        index=ProtoIndex(prototypes=[]),
        probe_iou=lambda *_a, **_kw: 1.0,
        gate=0.90,
        cap=2,
    )
    assert isinstance(result, PlanUnsupported)
    assert result.missing_op == "wb"


def test_plan_char_missing_mmh_returns_failed() -> None:
    result = plan_char(
        char="齉",
        cjk_entry={"operator": "a", "components": ["鼻", "囊"]},
        mmh=MINIMAL_MMH,
        index=ProtoIndex(prototypes=[]),
        probe_iou=lambda *_a, **_kw: 1.0,
        gate=0.90,
        cap=2,
    )
    assert isinstance(result, PlanFailed)
    assert "MMH" in result.reason


def test_plan_char_missing_component_mmh_returns_failed() -> None:
    partial_mmh = {
        "某": {"character": "某", "strokes": ["X0"] * 5, "medians": [[]] * 5},
        "甘": {"character": "甘", "strokes": ["G0"] * 3, "medians": [[]] * 3},
        # 木 missing intentionally.
    }
    result = plan_char(
        char="某",
        cjk_entry={"operator": "d", "components": ["甘", "木"]},
        mmh=partial_mmh,
        index=ProtoIndex(prototypes=[]),
        probe_iou=lambda *_a, **_kw: 1.0,
        gate=0.90,
        cap=2,
    )
    assert isinstance(result, PlanFailed)
    assert "木" in result.reason
    assert "standalone MMH" in result.reason


# -------- variant mint tests (Plan 09.2) --------


def test_plan_char_mints_variant_when_canonical_below_gate() -> None:
    """Canonical 木 exists; probe returns 0.5 -> mint variant proto:u6728_in_林
    with stroke_indices pointing into 林's MMH entry (matched by
    variant_match). variant_edges records the canonical->variant edge.

    Fixture geometry: 木's standalone strokes span the full canonical
    frame, and 林's first 4 strokes are those same strokes transformed
    into the left_right preset's left slot. The remaining 4 live in the
    right slot. The first occurrence mints the variant; the second
    occurrence reuses it.
    """
    left_paths = [
        _rect_path(0, 0, 100, 256),
        _rect_path(100, 256, 200, 512),
        _rect_path(200, 512, 300, 768),
        _rect_path(300, 768, 400, 1024),
    ]
    right_paths = [
        _rect_path(420, 0, 571, 256),
        _rect_path(571, 256, 722, 512),
        _rect_path(722, 512, 873, 768),
        _rect_path(873, 768, 1024, 1024),
    ]
    forest_paths = left_paths + right_paths

    mmh = {
        "林": {"character": "林", "strokes": forest_paths, "medians": [[]] * 8},
        "木": {
            "character": "木",
            "strokes": [
                _rect_path(0, 0, 256, 256),
                _rect_path(256, 256, 512, 512),
                _rect_path(512, 512, 768, 768),
                _rect_path(768, 768, 1024, 1024),
            ],
            "medians": [[]] * 4,
        },
    }
    existing_canonical = PrototypePlan(
        id=canonical_id("木"),
        name="木",
        from_char="木",
        stroke_indices=(0, 1, 2, 3),
        roles=("meaning",),
        anchors={},
    )
    result = plan_char(
        char="林",
        cjk_entry={"operator": "a", "components": ["木", "木"]},
        mmh=mmh,
        index=ProtoIndex(prototypes=[existing_canonical]),
        probe_iou=lambda *_a, **_kw: 0.5,
        gate=0.90,
        cap=2,
    )
    assert isinstance(result, PlanOk)
    variant_protos = [p for p in result.new_prototypes if p.id == variant_id("木", "林")]
    assert len(variant_protos) == 1
    variant = variant_protos[0]
    assert variant.from_char == "林"
    assert len(variant.stroke_indices) == 4
    assert all(0 <= i < 8 for i in variant.stroke_indices)
    assert (variant_id("木", "林"), canonical_id("木")) in result.variant_edges


def test_plan_char_below_floor_falls_back_to_canonical_reuse() -> None:
    """Canonical exists but the matcher's best pairing is below the
    per_stroke_floor (common when real MMH components cross slot
    boundaries). Rather than fail, the planner falls back to canonical
    reuse — the glyph renders with canonical strokes and the final
    compose-time IoU gate sorts verified vs needs_review, same as
    Plan 09.1. No variant is minted, no variant_of edge written."""
    canonical_paths = [_rect_path(0, 0, 100, 100), _rect_path(100, 100, 200, 200)]
    context_paths = [_rect_path(900, 900, 1024, 1024), _rect_path(950, 950, 1000, 1000)]
    mmh = {
        "XX": {"character": "XX", "strokes": context_paths, "medians": [[]] * 2},
        "木": {"character": "木", "strokes": canonical_paths, "medians": [[]] * 2},
    }
    existing_canonical = PrototypePlan(
        id=canonical_id("木"),
        name="木",
        from_char="木",
        stroke_indices=(0, 1),
        roles=("meaning",),
        anchors={},
    )
    result = plan_char(
        char="XX",
        cjk_entry={"operator": "a", "components": ["木", "木"]},
        mmh=mmh,
        index=ProtoIndex(prototypes=[existing_canonical]),
        probe_iou=lambda *_a, **_kw: 0.0,
        gate=0.90,
        cap=2,
    )
    assert isinstance(result, PlanOk)
    # No variant minted, no variant_of edge.
    assert result.new_prototypes == []
    assert result.variant_edges == []
    # Both component slots resolve to the canonical's id.
    assert [child.prototype_ref for child in result.glyph_plan.children] == [
        canonical_id("木"),
        canonical_id("木"),
    ]


def test_plan_char_fails_when_k_gt_m() -> None:
    """Canonical has more strokes than context slot can provide -> PlanFailed."""
    canonical_paths = [_rect_path(i * 10, 0, i * 10 + 5, 5) for i in range(5)]
    context_paths = [_rect_path(0, 0, 100, 100), _rect_path(200, 200, 300, 300)]
    mmh = {
        "CC": {"character": "CC", "strokes": context_paths, "medians": [[]] * 2},
        "木": {"character": "木", "strokes": canonical_paths, "medians": [[]] * 5},
    }
    existing_canonical = PrototypePlan(
        id=canonical_id("木"),
        name="木",
        from_char="木",
        stroke_indices=tuple(range(5)),
        roles=("meaning",),
        anchors={},
    )
    result = plan_char(
        char="CC",
        cjk_entry={"operator": "a", "components": ["木", "木"]},
        mmh=mmh,
        index=ProtoIndex(prototypes=[existing_canonical]),
        probe_iou=lambda *_a, **_kw: 0.0,
        gate=0.90,
        cap=2,
    )
    assert isinstance(result, PlanFailed)
    assert "k_gt_m" in result.reason.lower() or "more" in result.reason.lower()
