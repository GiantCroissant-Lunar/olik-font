"""Preset adapters: compute child transforms from canonical bboxes + params.

Each preset returns (resolved_children, constraints) where each resolved
child is a new InstancePlacement with `transform` set, and constraints is
a tuple of Primitive records describing what was enforced.
"""

from __future__ import annotations

from dataclasses import replace

from olik_font.constraints.primitives import (
    AlignX,
    AlignY,
    AnchorDistance,
    Inside,
    OrderX,
    OrderY,
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


def apply_top_bottom(
    top: InstancePlacement,
    bottom: InstancePlacement,
    glyph_bbox: BBox,
    weight_top: float = 0.49,
    gap: float = 20.0,
) -> tuple[InstancePlacement, InstancePlacement, tuple[Primitive, ...]]:
    gx0, gy0, gx1, gy1 = glyph_bbox
    height = gy1 - gy0
    split_y = gy0 + height * weight_top

    top_bbox: BBox = (gx0, gy0, gx1, split_y)
    bottom_bbox: BBox = (gx0, split_y + gap, gx1, gy1)

    top_out = replace(top, transform=bbox_to_bbox_affine(CANONICAL, top_bbox))
    bottom_out = replace(bottom, transform=bbox_to_bbox_affine(CANONICAL, bottom_bbox))

    constraints: tuple[Primitive, ...] = (
        AlignX(targets=(f"{top.instance_id}.center", f"{bottom.instance_id}.center")),
        OrderY(above=top.instance_id, below=bottom.instance_id),
        AnchorDistance(
            from_=f"{top.instance_id}.bottom",
            to=f"{bottom.instance_id}.top",
            value=gap,
        ),
    )
    return top_out, bottom_out, constraints


def apply_enclose(
    outer: InstancePlacement,
    inner: InstancePlacement,
    glyph_bbox: BBox,
    padding: float = 100.0,
) -> tuple[InstancePlacement, InstancePlacement, tuple[Primitive, ...]]:
    outer_bbox = glyph_bbox
    inner_bbox: BBox = (
        glyph_bbox[0] + padding,
        glyph_bbox[1] + padding,
        glyph_bbox[2] - padding,
        glyph_bbox[3] - padding,
    )
    outer_out = replace(outer, transform=bbox_to_bbox_affine(CANONICAL, outer_bbox))
    inner_out = replace(inner, transform=bbox_to_bbox_affine(CANONICAL, inner_bbox))

    constraints: tuple[Primitive, ...] = (
        Inside(target=inner.instance_id, frame=outer.instance_id, padding=padding),
        AlignX(targets=(f"{outer.instance_id}.center", f"{inner.instance_id}.center")),
        AlignY(targets=(f"{outer.instance_id}.center", f"{inner.instance_id}.center")),
    )
    return outer_out, inner_out, constraints


from olik_font.constraints.primitives import AvoidOverlap, Repeat  # noqa: E402


def apply_repeat_triangle(
    instances: tuple[InstancePlacement, InstancePlacement, InstancePlacement],
    glyph_bbox: BBox,
    scale: float = 0.5,
    avoid_padding: float = 8.0,
) -> tuple[tuple[InstancePlacement, InstancePlacement, InstancePlacement], tuple[Primitive, ...]]:
    if len(instances) != 3:
        raise ValueError(f"repeat_triangle requires 3 instances, got {len(instances)}")

    gx0, gy0, gx1, gy1 = glyph_bbox
    w = gx1 - gx0
    h = gy1 - gy0
    cell_w = w * scale
    cell_h = h * scale

    # top-center, bottom-left, bottom-right
    positions: list[BBox] = [
        (gx0 + (w - cell_w) / 2.0, gy0, gx0 + (w + cell_w) / 2.0, gy0 + cell_h),
        (gx0, gy1 - cell_h, gx0 + cell_w, gy1),
        (gx1 - cell_w, gy1 - cell_h, gx1, gy1),
    ]

    resolved: list[InstancePlacement] = []
    for inst, bbox in zip(instances, positions, strict=False):
        resolved.append(replace(inst, transform=bbox_to_bbox_affine(CANONICAL, bbox)))

    constraints: list[Primitive] = [
        Repeat(prototype_ref=instances[0].prototype_ref, count=3, layout_hint="triangle"),
    ]
    for i in range(3):
        for j in range(i + 1, 3):
            constraints.append(
                AvoidOverlap(
                    a=instances[i].instance_id, b=instances[j].instance_id, padding=avoid_padding
                )
            )

    return tuple(resolved), tuple(constraints)  # type: ignore[return-value]
