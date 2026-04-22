"""IoU-per-stroke Hungarian matching between a canonical component's
standalone strokes and a context character's strokes.

Used by the bulk auto-planner as an IoU probe that decides canonical-
reuse vs. context-variant. Both sides are measured: the caller passes a
measured `slot` bbox (typically the union bbox of the host's partition
strokes from MMH's `matches` field), and this module transforms the
canonical into that slot before computing bbox-IoU against the host's
native-frame strokes.

Variant stroke_indices are NOT derived from this matcher anymore — the
planner reads them directly from MMH's partition. Only the mean IoU
score is consumed by callers.

Algorithm: KxM cost matrix of `1 - bbox_iou`, solved with scipy's
`linear_sum_assignment` (Jonker-Volgenant, O(n^3) worst case but trivial
for <=30 strokes).
"""

from __future__ import annotations

from dataclasses import dataclass

from scipy.optimize import linear_sum_assignment

from olik_font.compose.iou import bbox_iou
from olik_font.geom import apply_affine_to_point, bbox_of_paths, bbox_to_bbox_affine, union_bbox
from olik_font.types import Affine, BBox


@dataclass(frozen=True)
class StrokePair:
    canonical_idx: int
    context_idx: int
    iou: float


@dataclass(frozen=True)
class MatchResult:
    pairs: tuple[StrokePair, ...]
    mean_iou: float
    min_iou: float
    k_gt_m: bool
    below_floor: bool


def _transform_bbox(bbox: BBox, affine: Affine) -> BBox:
    x0, y0, x1, y1 = bbox
    corners = (
        apply_affine_to_point(affine, (x0, y0)),
        apply_affine_to_point(affine, (x1, y0)),
        apply_affine_to_point(affine, (x1, y1)),
        apply_affine_to_point(affine, (x0, y1)),
    )
    xs = [p[0] for p in corners]
    ys = [p[1] for p in corners]
    return (min(xs), min(ys), max(xs), max(ys))


def match_in_slot(
    canonical_strokes: list[str],
    context_strokes: list[str],
    slot: BBox,
    per_stroke_floor: float = 0.30,
) -> MatchResult:
    """Hungarian bbox-IoU assignment of canonical strokes to context strokes.

    Args:
        canonical_strokes: SVG path-d strings of the canonical component's
            MMH entry (one per stroke), in canonical 0..1024 y-up space.
        context_strokes: SVG path-d strings of the context character's
            MMH entry (one per stroke), in context 0..1024 y-up space.
        slot: measured union bbox of the host's partition strokes for
            this component, typically computed by the planner from MMH's
            `matches` field.
        per_stroke_floor: any matched pair with IoU < floor flips
            `below_floor` to True. Caller decides whether to treat that
            as a hard failure.

    Returns:
        MatchResult. If `len(canonical_strokes) > len(context_strokes)`,
        returns immediately with k_gt_m=True and no pairs. If canonical
        is empty, returns a vacuously-perfect result (mean=1.0, no pairs).
    """
    k = len(canonical_strokes)
    m = len(context_strokes)

    if k == 0:
        return MatchResult(
            pairs=(),
            mean_iou=1.0,
            min_iou=1.0,
            k_gt_m=False,
            below_floor=False,
        )
    if k > m:
        return MatchResult(
            pairs=(),
            mean_iou=0.0,
            min_iou=0.0,
            k_gt_m=True,
            below_floor=False,
        )

    canonical_stroke_bboxes = [bbox_of_paths([path]) for path in canonical_strokes]
    canonical_union = union_bbox(tuple(canonical_stroke_bboxes))
    affine = bbox_to_bbox_affine(canonical_union, slot)
    canonical_in_slot = [_transform_bbox(bbox, affine) for bbox in canonical_stroke_bboxes]

    context_bboxes = [bbox_of_paths([path]) for path in context_strokes]
    cost = [
        [1.0 - bbox_iou(canonical_bbox, context_bbox) for context_bbox in context_bboxes]
        for canonical_bbox in canonical_in_slot
    ]

    row_ind, col_ind = linear_sum_assignment(cost)

    pairs: list[StrokePair] = []
    ious: list[float] = []
    for i, j in zip(row_ind, col_ind, strict=False):
        iou = 1.0 - cost[i][j]
        pairs.append(StrokePair(canonical_idx=int(i), context_idx=int(j), iou=iou))
        ious.append(iou)

    mean = sum(ious) / len(ious)
    minimum = min(ious)

    return MatchResult(
        pairs=tuple(pairs),
        mean_iou=mean,
        min_iou=minimum,
        k_gt_m=False,
        below_floor=minimum < per_stroke_floor,
    )
