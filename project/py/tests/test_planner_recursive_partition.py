from __future__ import annotations

from olik_font.bulk.planner import PlanOk, plan_char
from olik_font.bulk.reuse import ProtoIndex, canonical_id


def _rect_path(x0: float, y0: float, x1: float, y1: float) -> str:
    return f"M{x0},{y0} L{x1},{y0} L{x1},{y1} L{x0},{y1} Z"


def _host_entry(char: str, stroke_count: int) -> dict[str, object]:
    return {
        "character": char,
        "strokes": [_rect_path(i * 32, 0, i * 32 + 24, 24) for i in range(stroke_count)],
        "medians": [[]] * stroke_count,
    }


def _leaf_entry(char: str) -> dict[str, object]:
    return {
        "character": char,
        "strokes": [_rect_path(0, 0, 256, 256)],
        "medians": [[]],
    }


def _run_recursive_plan(
    *,
    char: str,
    cjk_entry: dict[str, object],
    matches: list[list[int]],
    mmh: dict[str, dict[str, object]],
) -> PlanOk:
    result = plan_char(
        char=char,
        cjk_entry=cjk_entry,
        mmh=mmh,
        matches=matches,
        index=ProtoIndex(prototypes=[]),
        probe_iou=lambda *_a, **_kw: 1.0,
        gate=0.90,
        cap=4,
    )
    assert isinstance(result, PlanOk)
    return result


def test_plan_char_descends_into_recursive_partition_for_sen() -> None:
    result = _run_recursive_plan(
        char="森",
        cjk_entry={
            "operator": "b",
            "components": ["木", "林"],
            "component_tree": [
                {"char": "木", "components": []},
                {
                    "char": "林",
                    "components": [
                        {"char": "木", "components": []},
                        {"char": "木", "components": []},
                    ],
                },
            ],
        },
        matches=[[0], [1, 0], [1, 1]],
        mmh={
            "森": _host_entry("森", 3),
            "木": _leaf_entry("木"),
        },
    )

    assert len(result.glyph_plan.children) == 2
    top, lower_pair = result.glyph_plan.children
    assert top.mode == "keep"
    assert top.source_stroke_indices == (0,)
    assert lower_pair.mode == "refine"
    assert lower_pair.source_stroke_indices is None
    assert [child.source_stroke_indices for child in lower_pair.children] == [(1,), (2,)]
    assert [p.id for p in result.new_prototypes] == [canonical_id("木")]


def test_plan_char_descends_into_recursive_partition_for_gai() -> None:
    result = _run_recursive_plan(
        char="丐",
        cjk_entry={
            "operator": "d/t",
            "components": ["下", "㇉"],
            "component_tree": [
                {
                    "char": "下",
                    "components": [
                        {"char": "㇐", "components": []},
                        {"char": "卜", "components": []},
                    ],
                },
                {"char": "㇉", "components": []},
            ],
        },
        matches=[[0, 0], [0, 1], [1]],
        mmh={
            "丐": _host_entry("丐", 3),
            "㇐": _leaf_entry("㇐"),
            "卜": _leaf_entry("卜"),
            "㇉": _leaf_entry("㇉"),
        },
    )

    assert len(result.glyph_plan.children) == 2
    top_bar, hook = result.glyph_plan.children
    assert top_bar.mode == "refine"
    assert [child.source_stroke_indices for child in top_bar.children] == [(0,), (1,)]
    assert hook.mode == "keep"
    assert hook.source_stroke_indices == (2,)
    assert {p.id for p in result.new_prototypes} == {
        canonical_id("㇐"),
        canonical_id("卜"),
        canonical_id("㇉"),
    }


def test_plan_char_handles_single_leaf_entry_for_yi() -> None:
    result = _run_recursive_plan(
        char="乙",
        cjk_entry={
            "operator": "me",
            "components": ["㇠"],
            "component_tree": [{"char": "㇠", "components": []}],
        },
        matches=[[0]],
        mmh={
            "乙": _host_entry("乙", 1),
            "㇠": _leaf_entry("㇠"),
        },
    )

    assert len(result.glyph_plan.children) == 1
    leaf = result.glyph_plan.children[0]
    assert leaf.mode == "keep"
    assert leaf.source_stroke_indices == (0,)
    assert [p.id for p in result.new_prototypes] == [canonical_id("㇠")]


def test_plan_char_descends_into_recursive_partition_for_zhao() -> None:
    result = _run_recursive_plan(
        char="兆",
        cjk_entry={
            "operator": "w",
            "components": ["儿", "37036"],
            "component_tree": [
                {"char": "儿", "components": []},
                {
                    "char": "37036",
                    "components": [
                        {"char": "冫", "components": []},
                        {"char": "90011", "components": []},
                    ],
                },
            ],
        },
        matches=[[0], [1, 0], [1, 1]],
        mmh={
            "兆": _host_entry("兆", 3),
            "儿": _leaf_entry("儿"),
            "冫": _leaf_entry("冫"),
            "90011": _leaf_entry("90011"),
        },
    )

    assert len(result.glyph_plan.children) == 2
    legs, splash = result.glyph_plan.children
    assert legs.mode == "keep"
    assert legs.source_stroke_indices == (0,)
    assert splash.mode == "refine"
    assert [child.source_stroke_indices for child in splash.children] == [(1,), (2,)]
    assert {p.id for p in result.new_prototypes} == {
        canonical_id("儿"),
        canonical_id("冫"),
        canonical_id("90011"),
    }
