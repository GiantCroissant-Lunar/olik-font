"""Parse MMH dictionary.txt `matches` field into per-component stroke partitions.

MMH's per-character `matches` field assigns every stroke to one of the
top-level IDS components. For 明 (⿰日月) the field is::

    [[0], [0], [0], [0], [1], [1], [1], [1]]

→ strokes 0..3 belong to component 0 (日), strokes 4..7 to component 1 (月).

For nested composites like 森 (⿱木⿰木木) the inner path is encoded with
a longer list::

    [[0], [0], [0], [0], [1, 0], [1, 0], [1, 0], [1, 0], [1, 1], [1, 1], [1, 1], [1, 1]]

→ top-level partition: {0: [0,1,2,3], 1: [4..11]}; nested under 1:
{(1,0): [4,5,6,7], (1,1): [8,9,10,11]}.

This module turns that raw structure into an explicit per-instance list
of stroke indices that downstream compose can measure against MMH paths.
It supersedes the preset / slot_bbox machinery for characters whose MMH
entry carries `matches`. Characters without `matches` (older/rare glyphs)
fall through and are handled by the Hungarian matcher path with a
measured slot instead of a preset one.
"""

from __future__ import annotations

from collections.abc import Sequence


def _partition_for_prefix(
    matches: Sequence[Sequence[int] | None] | None,
    prefix: tuple[int, ...],
) -> list[list[int]] | None:
    if not matches:
        return None
    buckets: dict[int, list[int]] = {}
    depth = len(prefix)
    for stroke_idx, assignment in enumerate(matches):
        if not assignment or len(assignment) <= depth:
            continue
        if prefix and tuple(int(v) for v in assignment[:depth]) != prefix:
            continue
        next_idx = int(assignment[depth])
        buckets.setdefault(next_idx, []).append(stroke_idx)
    if not buckets:
        return None
    return [list(buckets[k]) for k in sorted(buckets)]


def top_level_partition(matches: Sequence[Sequence[int] | None] | None) -> list[list[int]] | None:
    """Return per-top-level-component stroke indices from an MMH matches field.

    Returns None when `matches` is None or empty (character not partitioned
    in MMH's data). Otherwise the list is indexed by top-level component
    index — `out[i]` is the list of stroke indices belonging to component i.
    """
    return _partition_for_prefix(matches, ())


def nested_partition(
    matches: Sequence[Sequence[int] | None] | None,
    top_level_idx: int | None = None,
    *,
    path_prefix: Sequence[int] | None = None,
) -> list[list[int]] | None:
    """Return per-sub-component stroke indices for one top-level component.

    Used for chars like 森 whose top-level component 1 itself decomposes
    (⿰木木). Returns None when no nested partition exists at the requested
    position. Stroke indices are in the ORIGINAL character's frame —
    caller can feed them directly to `measure_instance_transform`.
    """
    if path_prefix is not None:
        return _partition_for_prefix(matches, tuple(int(v) for v in path_prefix))
    if top_level_idx is None:
        raise ValueError("nested_partition needs top_level_idx or path_prefix")
    return _partition_for_prefix(matches, (int(top_level_idx),))
