"""plan_char — auto-build ExtractionPlan fragments from cjk-decomp."""

from __future__ import annotations

from olik_font.bulk.planner import (
    PlanFailed,
    PlanOk,
    PlanUnsupported,
    plan_char,
)
from olik_font.bulk.reuse import ProtoIndex, canonical_id

# Plan 09.1: canonicals are extracted from the component's OWN standalone
# MMH entry, so the fixture must include an entry for every component
# referenced by the cjk-decomp of the char-under-test.
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
        probe_iou=lambda _: 1.0,
        gate=0.90,
        cap=2,
    )
    assert isinstance(result, PlanOk)
    assert result.glyph_plan.preset == "left_right"
    assert len(result.glyph_plan.children) == 2
    # Auto-planned canonicals use codepoint slugs (u<hex>) — friendly
    # slugs like proto:sun stay reserved for the hand-tuned seed rows.
    assert {p.id for p in result.new_prototypes} == {
        canonical_id("日"),
        canonical_id("月"),
    }
    # Each new proto carries ALL strokes from its OWN standalone MMH
    # entry (4 for 日, 4 for 月), NOT a naive split of 明's 8 strokes.
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
        probe_iou=lambda _: 1.0,
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
        probe_iou=lambda _: 1.0,
        gate=0.90,
        cap=2,
    )
    assert isinstance(result, PlanFailed)
    assert "MMH" in result.reason


def test_plan_char_missing_component_mmh_returns_failed() -> None:
    """If a component has no standalone MMH entry, refuse to mint a
    canonical with context-split strokes — fail honestly so the glyph
    lands as a stub row for a later plan with better data."""
    partial_mmh = {
        "某": {"character": "某", "strokes": ["X0"] * 5, "medians": [[]] * 5},
        # 甘 present
        "甘": {"character": "甘", "strokes": ["G0"] * 3, "medians": [[]] * 3},
        # but 木 missing
    }
    result = plan_char(
        char="某",
        cjk_entry={"operator": "d", "components": ["甘", "木"]},
        mmh=partial_mmh,
        index=ProtoIndex(prototypes=[]),
        probe_iou=lambda _: 1.0,
        gate=0.90,
        cap=2,
    )
    assert isinstance(result, PlanFailed)
    assert "木" in result.reason
    assert "standalone MMH" in result.reason


def test_plan_char_low_iou_returns_failed_no_variant() -> None:
    """Plan 09.1 intentionally does NOT mint context-variant prototypes
    (MMH lacks per-stroke matches to do it correctly). If canonical
    reuse fails the IoU gate, return PlanFailed so the glyph lands as
    needs_review, not with wrong strokes.
    """
    from olik_font.prototypes.extraction_plan import PrototypePlan

    existing = [
        PrototypePlan(
            id=canonical_id("月"),
            name="月",
            from_char="月",
            stroke_indices=(0, 1, 2, 3),
            roles=("meaning",),
            anchors={},
        ),
    ]
    result = plan_char(
        char="朔",
        cjk_entry={"operator": "a", "components": ["屰", "月"]},
        mmh={
            **MINIMAL_MMH,
            "朔": MINIMAL_MMH["明"],
            "屰": MINIMAL_MMH["日"],
        },
        index=ProtoIndex(prototypes=existing),
        probe_iou=lambda _: 0.5,  # canonical 月 fails
        gate=0.90,
        cap=2,
    )
    assert isinstance(result, PlanFailed)
    assert "IoU" in result.reason or "variant" in result.reason
