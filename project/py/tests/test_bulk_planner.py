"""plan_char — build a measured-coordinate GlyphPlan from cjk-decomp + MMH `matches`."""

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


# MMH entries used throughout: the host char AND every named component
# must have a standalone entry (Plan 09.1 invariant).
def _d_stroke(i: int) -> str:
    base = 64 + i * 8
    return _rect_path(base, 0, base + 8, 8)


MINIMAL_MMH = {
    "明": {
        "character": "明",
        "strokes": [_d_stroke(i) for i in range(8)],
        "medians": [[]] * 8,
    },
    "日": {"character": "日", "strokes": [_rect_path(0, 0, 256, 256)] * 4, "medians": [[]] * 4},
    "月": {"character": "月", "strokes": [_rect_path(0, 0, 256, 256)] * 4, "medians": [[]] * 4},
}

# partition for 明: strokes 0..3 → 日, 4..7 → 月.
MATCHES_MING: list[list[int]] = [[0], [0], [0], [0], [1], [1], [1], [1]]


def test_plan_char_supported_op_returns_ok() -> None:
    result = plan_char(
        char="明",
        cjk_entry={"operator": "a", "components": ["日", "月"]},
        mmh=MINIMAL_MMH,
        matches=MATCHES_MING,
        index=ProtoIndex(prototypes=[]),
        probe_iou=lambda *_a, **_kw: 1.0,
        gate=0.90,
        cap=2,
    )
    assert isinstance(result, PlanOk)
    # No preset vocabulary anywhere on the emitted plan.
    assert not hasattr(result.glyph_plan, "preset")
    assert len(result.glyph_plan.children) == 2
    left, right = result.glyph_plan.children
    assert left.source_stroke_indices == (0, 1, 2, 3)
    assert right.source_stroke_indices == (4, 5, 6, 7)
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
        matches=None,
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
        matches=MATCHES_MING,
        index=ProtoIndex(prototypes=[]),
        probe_iou=lambda *_a, **_kw: 1.0,
        gate=0.90,
        cap=2,
    )
    assert isinstance(result, PlanFailed)
    assert "MMH" in result.reason


def test_plan_char_missing_partition_returns_failed() -> None:
    result = plan_char(
        char="明",
        cjk_entry={"operator": "a", "components": ["日", "月"]},
        mmh=MINIMAL_MMH,
        matches=None,  # simulate char without MMH matches coverage
        index=ProtoIndex(prototypes=[]),
        probe_iou=lambda *_a, **_kw: 1.0,
        gate=0.90,
        cap=2,
    )
    assert isinstance(result, PlanFailed)
    assert "partition" in result.reason.lower() or "matches" in result.reason.lower()


def test_plan_char_partition_arity_mismatch_returns_failed() -> None:
    # 明 has 2 cjk components but a partition with 3 buckets.
    bad_matches: list[list[int]] = [[0], [1], [2]] + [[0]] * 5
    result = plan_char(
        char="明",
        cjk_entry={"operator": "a", "components": ["日", "月"]},
        mmh=MINIMAL_MMH,
        matches=bad_matches,
        index=ProtoIndex(prototypes=[]),
        probe_iou=lambda *_a, **_kw: 1.0,
        gate=0.90,
        cap=2,
    )
    assert isinstance(result, PlanFailed)
    assert "partition" in result.reason.lower()


def test_plan_char_variant_mint_uses_partition_indices() -> None:
    """When canonical probe fails the variant's stroke_indices come from
    the partition directly (not from Hungarian re-assignment)."""
    forest_paths = [_rect_path(i * 100, 0, (i + 1) * 100, 1024) for i in range(8)]
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
    matches_forest = [[0], [0], [0], [0], [1], [1], [1], [1]]
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
        matches=matches_forest,
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
    assert variant.stroke_indices == (0, 1, 2, 3)
    assert (variant_id("木", "林"), canonical_id("木")) in result.variant_edges
    # The SECOND 木 instance reuses the minted variant — source_stroke_indices
    # still comes from the partition (4..7).
    left, right = result.glyph_plan.children
    assert left.source_stroke_indices == (0, 1, 2, 3)
    assert right.source_stroke_indices == (4, 5, 6, 7)
