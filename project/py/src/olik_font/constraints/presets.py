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
from olik_font.geom import bbox_to_bbox_affine, fit_in_slot
from olik_font.types import BBox, InstancePlacement

CANONICAL: BBox = (0.0, 0.0, 1024.0, 1024.0)
_LEFT_RIGHT_WEIGHT_L = 400.0 / 1024.0
_LEFT_RIGHT_GAP = 20.0
_TOP_BOTTOM_WEIGHT_TOP = 0.49
_TOP_BOTTOM_GAP = 20.0
_ENCLOSE_PADDING = 100.0
_REPEAT_TRIANGLE_SCALE = 0.5


def _slot_bbox_left_right(
    slot_idx: int,
    glyph_bbox: BBox,
    *,
    weight_l: float = _LEFT_RIGHT_WEIGHT_L,
    gap: float = _LEFT_RIGHT_GAP,
) -> BBox:
    gx0, gy0, gx1, gy1 = glyph_bbox
    width = gx1 - gx0
    split_x = gx0 + width * weight_l
    if slot_idx == 0:
        return (gx0, gy0, split_x, gy1)
    if slot_idx == 1:
        return (split_x + gap, gy0, gx1, gy1)
    raise ValueError(f"slot_idx {slot_idx} out of range for left_right (0..1)")


def _slot_bbox_top_bottom(
    slot_idx: int,
    glyph_bbox: BBox,
    *,
    weight_top: float = _TOP_BOTTOM_WEIGHT_TOP,
    gap: float = _TOP_BOTTOM_GAP,
) -> BBox:
    # y-up: VISUAL TOP sits at HIGH y, VISUAL BOTTOM at LOW y.
    # See apply_top_bottom docstring for the full explanation.
    gx0, gy0, gx1, gy1 = glyph_bbox
    height = gy1 - gy0
    split_y = gy0 + height * (1.0 - weight_top)
    if slot_idx == 0:
        return (gx0, split_y + gap, gx1, gy1)
    if slot_idx == 1:
        return (gx0, gy0, gx1, split_y)
    raise ValueError(f"slot_idx {slot_idx} out of range for top_bottom (0..1)")


def _slot_bbox_enclose(
    slot_idx: int,
    glyph_bbox: BBox,
    *,
    padding: float = _ENCLOSE_PADDING,
) -> BBox:
    if slot_idx == 0:
        return glyph_bbox
    if slot_idx == 1:
        gx0, gy0, gx1, gy1 = glyph_bbox
        return (
            gx0 + padding,
            gy0 + padding,
            gx1 - padding,
            gy1 - padding,
        )
    raise ValueError(f"slot_idx {slot_idx} out of range for enclose (0..1)")


def _slot_bbox_repeat_triangle(
    slot_idx: int,
    glyph_bbox: BBox,
    *,
    scale: float = _REPEAT_TRIANGLE_SCALE,
) -> BBox:
    # y-up: top-center at HIGH y; two bottom cells at LOW y.
    gx0, gy0, gx1, gy1 = glyph_bbox
    w = gx1 - gx0
    h = gy1 - gy0
    cell_w = w * scale
    cell_h = h * scale
    if slot_idx == 0:
        return (gx0 + (w - cell_w) / 2.0, gy1 - cell_h, gx0 + (w + cell_w) / 2.0, gy1)
    if slot_idx == 1:
        return (gx0, gy0, gx0 + cell_w, gy0 + cell_h)
    if slot_idx == 2:
        return (gx1 - cell_w, gy0, gx1, gy0 + cell_h)
    raise ValueError(f"slot_idx {slot_idx} out of range for repeat_triangle (0..2)")


def slot_bbox(
    preset: str,
    n_components: int,
    slot_idx: int,
    glyph_bbox: BBox = CANONICAL,
) -> BBox:
    """Return the y-up bbox for component `slot_idx` in `preset`.

    Shared helper used by both the renderers (apply_*) and the bulk
    variant-matching pipeline (bulk.variant_match). Keeping the bbox
    math in one place ensures the matcher's predicted slot matches
    exactly where the renderer will place the strokes.
    """
    del n_components
    if preset == "left_right":
        return _slot_bbox_left_right(slot_idx, glyph_bbox)
    if preset == "top_bottom":
        return _slot_bbox_top_bottom(slot_idx, glyph_bbox)
    if preset == "enclose":
        return _slot_bbox_enclose(slot_idx, glyph_bbox)
    if preset == "repeat_triangle":
        return _slot_bbox_repeat_triangle(slot_idx, glyph_bbox)
    raise ValueError(f"unknown preset: {preset!r}")


def apply_left_right(
    left: InstancePlacement,
    right: InstancePlacement,
    glyph_bbox: BBox,
    weight_l: float = 400.0 / 1024.0,
    gap: float = 20.0,
) -> tuple[InstancePlacement, InstancePlacement, tuple[Primitive, ...]]:
    # Plan 09.1 pinned weight/gap to module-level constants; keep the
    # keyword signature for call-site compatibility but ignore overrides.
    del weight_l, gap
    slot_0 = _slot_bbox_left_right(0, glyph_bbox)
    slot_1 = _slot_bbox_left_right(1, glyph_bbox)

    # Plan 10.1: anchor canonical top-left inside each slot so radicals
    # don't get non-uniformly stretched.
    left_target = fit_in_slot(CANONICAL, slot_0, "top-left")
    right_target = fit_in_slot(CANONICAL, slot_1, "top-left")

    left_out = replace(left, transform=bbox_to_bbox_affine(CANONICAL, left_target))
    right_out = replace(right, transform=bbox_to_bbox_affine(CANONICAL, right_target))

    constraints: tuple[Primitive, ...] = (
        AlignY(targets=(f"{left.instance_id}.center", f"{right.instance_id}.center")),
        OrderX(before=left.instance_id, after=right.instance_id),
        AnchorDistance(
            from_=f"{left.instance_id}.right_edge",
            to=f"{right.instance_id}.left_edge",
            value=_LEFT_RIGHT_GAP,
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
    del weight_top, gap
    slot_0 = _slot_bbox_top_bottom(0, glyph_bbox)
    slot_1 = _slot_bbox_top_bottom(1, glyph_bbox)

    # Plan 10.1: top component hugs top-center of its slot; bottom
    # hugs bottom-center of its slot.
    top_target = fit_in_slot(CANONICAL, slot_0, "top-center")
    bottom_target = fit_in_slot(CANONICAL, slot_1, "bottom-center")

    top_out = replace(top, transform=bbox_to_bbox_affine(CANONICAL, top_target))
    bottom_out = replace(bottom, transform=bbox_to_bbox_affine(CANONICAL, bottom_target))

    constraints: tuple[Primitive, ...] = (
        AlignX(targets=(f"{top.instance_id}.center", f"{bottom.instance_id}.center")),
        OrderY(above=top.instance_id, below=bottom.instance_id),
        AnchorDistance(
            from_=f"{top.instance_id}.bottom",
            to=f"{bottom.instance_id}.top",
            value=_TOP_BOTTOM_GAP,
        ),
    )
    return top_out, bottom_out, constraints


def apply_enclose(
    outer: InstancePlacement,
    inner: InstancePlacement,
    glyph_bbox: BBox,
    padding: float = 100.0,
) -> tuple[InstancePlacement, InstancePlacement, tuple[Primitive, ...]]:
    outer_bbox = _slot_bbox_enclose(0, glyph_bbox, padding=padding)
    inner_bbox = _slot_bbox_enclose(1, glyph_bbox, padding=padding)
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

    # y-up convention (see apply_top_bottom): the visual TOP position
    # has high y; the two BOTTOM positions have low y. After the render-
    # time flip this becomes 1 instance at the visual top-center plus 2
    # instances at the visual bottom-left / bottom-right.
    positions = [
        _slot_bbox_repeat_triangle(0, glyph_bbox, scale=scale),
        _slot_bbox_repeat_triangle(1, glyph_bbox, scale=scale),
        _slot_bbox_repeat_triangle(2, glyph_bbox, scale=scale),
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
