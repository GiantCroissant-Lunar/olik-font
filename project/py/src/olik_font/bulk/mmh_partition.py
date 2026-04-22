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


def top_level_partition(matches: Sequence[Sequence[int] | None] | None) -> list[list[int]] | None:
    """Return per-top-level-component stroke indices from an MMH matches field.

    Returns None when `matches` is None or empty (character not partitioned
    in MMH's data). Otherwise the list is indexed by top-level component
    index — `out[i]` is the list of stroke indices belonging to component i.
    """
    if not matches:
        return None
    buckets: dict[int, list[int]] = {}
    for stroke_idx, assignment in enumerate(matches):
        if not assignment:
            return None
        top = int(assignment[0])
        buckets.setdefault(top, []).append(stroke_idx)
    if not buckets:
        return None
    ordered: list[list[int]] = []
    for k in sorted(buckets):
        ordered.append(list(buckets[k]))
    return ordered


def nested_partition(
    matches: Sequence[Sequence[int] | None] | None,
    top_level_idx: int,
) -> list[list[int]] | None:
    """Return per-sub-component stroke indices for one top-level component.

    Used for chars like 森 whose top-level component 1 itself decomposes
    (⿰木木). Returns None when no nested partition exists at the requested
    position. Stroke indices are in the ORIGINAL character's frame —
    caller can feed them directly to `measure_instance_transform`.
    """
    if not matches:
        return None
    buckets: dict[int, list[int]] = {}
    for stroke_idx, assignment in enumerate(matches):
        if not assignment or len(assignment) < 2:
            continue
        if int(assignment[0]) != top_level_idx:
            continue
        sub = int(assignment[1])
        buckets.setdefault(sub, []).append(stroke_idx)
    if not buckets:
        return None
    return [list(buckets[k]) for k in sorted(buckets)]
