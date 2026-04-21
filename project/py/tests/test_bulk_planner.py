"""plan_char — auto-build ExtractionPlan fragments from cjk-decomp."""

from __future__ import annotations

from olik_font.bulk.planner import (
    PlanFailed,
    PlanOk,
    PlanUnsupported,
    plan_char,
)
from olik_font.bulk.reuse import ProtoIndex

MINIMAL_MMH = {
    "明": {
        "character": "明",
        "strokes": ["M0", "M1", "M2", "M3", "M4", "M5", "M6", "M7"],
        "medians": [[]] * 8,
    },
    "日": {"character": "日", "strokes": ["M0"] * 4, "medians": [[]] * 4},
    "月": {"character": "月", "strokes": ["M0"] * 4, "medians": [[]] * 4},
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
    assert {p.id for p in result.new_prototypes} == {"proto:sun", "proto:moon"}


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


def test_plan_char_variant_cap_exceeded_returns_failed() -> None:
    from olik_font.prototypes.extraction_plan import PrototypePlan

    existing = [
        PrototypePlan(
            id="proto:moon",
            name="月",
            from_char="明",
            stroke_indices=(0, 1, 2, 3),
            roles=("meaning",),
            anchors={},
        ),
        PrototypePlan(
            id="proto:moon_in_朋",
            name="月",
            from_char="朋",
            stroke_indices=(0, 1, 2, 3),
            roles=("meaning",),
            anchors={},
        ),
        PrototypePlan(
            id="proto:moon_in_期",
            name="月",
            from_char="期",
            stroke_indices=(0, 1, 2, 3),
            roles=("meaning",),
            anchors={},
        ),
    ]
    result = plan_char(
        char="朔",
        cjk_entry={"operator": "a", "components": ["屰", "月"]},
        mmh={**MINIMAL_MMH, "朔": MINIMAL_MMH["明"], "屰": MINIMAL_MMH["日"]},
        index=ProtoIndex(prototypes=existing),
        probe_iou=lambda _: 0.5,
        gate=0.90,
        cap=2,
    )
    assert isinstance(result, PlanFailed)
    assert "cap" in result.reason.lower()
