"""Secondary geometry QA metrics for emitted glyph records."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence

from olik_font.geom import BBox, bbox_of_paths, normalize_paths_to_canonical
from olik_font.types import Point

_CANVAS_SCALE = 1024.0


def glyph_centroid(record: Mapping[str, object]) -> Point:
    """Return the weighted centroid of the composed stroke set."""
    return _weighted_centroid(_composed_bboxes(record))


def centroid_distance(record: Mapping[str, object]) -> float:
    """Distance between composed centroid and the normalized MMH centroid."""
    composed = glyph_centroid(record)
    expected = _expected_centroid(record)
    return math.dist(composed, expected)


def inertia_spread(record: Mapping[str, object]) -> float:
    """Normalized second moment of the composed stroke distribution."""
    bboxes = _composed_bboxes(record)
    centroid = _weighted_centroid(bboxes)
    numerator = 0.0
    denominator = 0.0
    for bbox in bboxes:
        cx, cy = _bbox_center(bbox)
        weight = _bbox_weight(bbox)
        numerator += weight * ((cx - centroid[0]) ** 2 + (cy - centroid[1]) ** 2)
        denominator += weight
    if denominator == 0.0:
        return 0.0
    return numerator / denominator / (_CANVAS_SCALE**2)


def _expected_centroid(record: Mapping[str, object]) -> Point:
    mmh_bboxes = _normalized_mmh_bboxes(record.get("mmh_strokes"))
    if mmh_bboxes:
        return _weighted_centroid(mmh_bboxes)
    root_bbox = _layout_root_bbox(record)
    return _bbox_center(root_bbox) if root_bbox is not None else glyph_centroid(record)


def _composed_bboxes(record: Mapping[str, object]) -> tuple[BBox, ...]:
    instances = record.get("stroke_instances")
    if not isinstance(instances, Sequence):
        return ()
    bboxes: list[BBox] = []
    for instance in instances:
        if not isinstance(instance, Mapping):
            continue
        bbox = _bbox_value(instance.get("bbox"))
        if bbox is not None:
            bboxes.append(bbox)
            continue
        path = instance.get("path")
        if isinstance(path, str):
            bboxes.append(bbox_of_paths([path]))
    return tuple(bboxes)


def _layout_root_bbox(record: Mapping[str, object]) -> BBox | None:
    layout_tree = record.get("layout_tree")
    if not isinstance(layout_tree, Mapping):
        return None
    return _bbox_value(layout_tree.get("bbox"))


def _weighted_centroid(bboxes: tuple[BBox, ...]) -> Point:
    if not bboxes:
        return (_CANVAS_SCALE / 2.0, _CANVAS_SCALE / 2.0)
    total_x = 0.0
    total_y = 0.0
    total_weight = 0.0
    for bbox in bboxes:
        weight = _bbox_weight(bbox)
        cx, cy = _bbox_center(bbox)
        total_x += weight * cx
        total_y += weight * cy
        total_weight += weight
    if total_weight == 0.0:
        return (_CANVAS_SCALE / 2.0, _CANVAS_SCALE / 2.0)
    return (total_x / total_weight, total_y / total_weight)


def _bbox_weight(bbox: BBox) -> float:
    width = max(0.0, bbox[2] - bbox[0])
    height = max(0.0, bbox[3] - bbox[1])
    area = width * height
    if area > 0.0:
        return area
    span = max(width, height)
    return span if span > 0.0 else 1.0


def _bbox_center(bbox: BBox) -> Point:
    return ((bbox[0] + bbox[2]) / 2.0, (bbox[1] + bbox[3]) / 2.0)


def _bbox_value(value: object) -> BBox | None:
    if not isinstance(value, Sequence) or len(value) != 4:
        return None
    coords = tuple(float(coord) for coord in value)
    return (coords[0], coords[1], coords[2], coords[3])


def _normalized_mmh_bboxes(value: object) -> tuple[BBox, ...]:
    mmh_paths = tuple(_string_list(value))
    if not mmh_paths:
        return ()
    try:
        normalized, _ = normalize_paths_to_canonical(
            mmh_paths, (0.0, 0.0, _CANVAS_SCALE, _CANVAS_SCALE)
        )
    except Exception:
        return ()
    bboxes: list[BBox] = []
    for path in normalized:
        try:
            bboxes.append(bbox_of_paths([path]))
        except Exception:
            continue
    return tuple(bboxes)


def _string_list(value: object) -> tuple[str, ...]:
    if not isinstance(value, Sequence):
        return ()
    return tuple(item for item in value if isinstance(item, str))
