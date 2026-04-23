"""Partition MMH's `matches` field into per-component stroke indices."""

from __future__ import annotations

from olik_font.bulk.mmh_partition import nested_partition, top_level_partition


def test_top_level_simple_two_components() -> None:
    # 明 — strokes 0..3 belong to component 0 (日), 4..7 to component 1 (月).
    matches = [[0], [0], [0], [0], [1], [1], [1], [1]]
    assert top_level_partition(matches) == [[0, 1, 2, 3], [4, 5, 6, 7]]


def test_top_level_non_contiguous_enclosure() -> None:
    # 國 ⿴囗或 — 囗 is strokes 0, 1, 10 (closes the box last); 或 is 2..9.
    matches = [[0], [0], [1], [1], [1], [1], [1], [1], [1], [1], [0]]
    parts = top_level_partition(matches)
    assert parts == [[0, 1, 10], [2, 3, 4, 5, 6, 7, 8, 9]]


def test_top_level_nested_pins_to_outer() -> None:
    # 森 ⿱木⿰木木 — strokes 0..3 belong to the top 木 (component 0),
    # the rest to the nested subtree rooted at component 1.
    matches = [
        [0],
        [0],
        [0],
        [0],
        [1, 0],
        [1, 0],
        [1, 0],
        [1, 0],
        [1, 1],
        [1, 1],
        [1, 1],
        [1, 1],
    ]
    parts = top_level_partition(matches)
    assert parts == [[0, 1, 2, 3], [4, 5, 6, 7, 8, 9, 10, 11]]


def test_top_level_none_when_missing() -> None:
    assert top_level_partition(None) is None
    assert top_level_partition([]) is None


def test_nested_partition_for_deep_component() -> None:
    matches = [
        [0],
        [0],
        [0],
        [0],
        [1, 0],
        [1, 0],
        [1, 0],
        [1, 0],
        [1, 1],
        [1, 1],
        [1, 1],
        [1, 1],
    ]
    nested = nested_partition(matches, top_level_idx=1)
    assert nested == [[4, 5, 6, 7], [8, 9, 10, 11]]


def test_nested_partition_none_when_no_children() -> None:
    # 明 has no nested partition under either top-level component.
    matches = [[0], [0], [0], [0], [1], [1], [1], [1]]
    assert nested_partition(matches, top_level_idx=0) is None
    assert nested_partition(matches, top_level_idx=1) is None
