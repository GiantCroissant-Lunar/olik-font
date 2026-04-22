"""Measurement helpers for per-instance placement in MMH source space."""

from __future__ import annotations

from collections.abc import Sequence

from olik_font.geom import bbox_of_paths, bbox_to_bbox_affine
from olik_font.types import Affine, BBox

CANONICAL: BBox = (0.0, 0.0, 1024.0, 1024.0)


def measure_bbox_from_strokes(paths: Sequence[str]) -> BBox:
    return bbox_of_paths(tuple(paths))


def measure_instance_transform(
    mmh_paths_at_indices: Sequence[str],
    canonical: BBox = CANONICAL,
) -> Affine:
    bbox = measure_bbox_from_strokes(mmh_paths_at_indices)
    return bbox_to_bbox_affine(canonical, bbox)
