"""Preset adapters: compute child transforms from canonical bboxes + params.

Each preset returns (resolved_children, constraints) where each resolved
child is a new InstancePlacement with `transform` set, and constraints is
a tuple of Primitive records describing what was enforced.
"""

from __future__ import annotations

from dataclasses import replace

from olik_font.constraints.primitives import (
    AlignY,
    AnchorDistance,
    OrderX,
    Primitive,
)
from olik_font.geom import bbox_to_bbox_affine
from olik_font.types import BBox, InstancePlacement

CANONICAL: BBox = (0.0, 0.0, 1024.0, 1024.0)


def apply_left_right(
    left: InstancePlacement,
    right: InstancePlacement,
    glyph_bbox: BBox,
    weight_l: float = 400.0 / 1024.0,
    gap: float = 20.0,
) -> tuple[InstancePlacement, InstancePlacement, tuple[Primitive, ...]]:
    gx0, gy0, gx1, gy1 = glyph_bbox
    width = gx1 - gx0
    split_x = gx0 + width * weight_l

    left_bbox: BBox = (gx0, gy0, split_x, gy1)
    right_bbox: BBox = (split_x + gap, gy0, gx1, gy1)

    left_out = replace(left, transform=bbox_to_bbox_affine(CANONICAL, left_bbox))
    right_out = replace(right, transform=bbox_to_bbox_affine(CANONICAL, right_bbox))

    constraints: tuple[Primitive, ...] = (
        AlignY(targets=(f"{left.instance_id}.center", f"{right.instance_id}.center")),
        OrderX(before=left.instance_id, after=right.instance_id),
        AnchorDistance(
            from_=f"{left.instance_id}.right_edge",
            to=f"{right.instance_id}.left_edge",
            value=gap,
        ),
    )
    return left_out, right_out, constraints
