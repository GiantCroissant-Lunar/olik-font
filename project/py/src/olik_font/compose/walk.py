"""Post-order walk over InstancePlacement trees; fills in transforms.

Dispatches by `input_adapter`:
  - "preset:left_right"     -> apply_left_right
  - "preset:top_bottom"     -> apply_top_bottom
  - "preset:enclose"        -> apply_enclose
  - "direct:repeat_triangle"-> apply_repeat_triangle
  - "direct" / "leaf"       -> keep transform; usually identity at root

Refine-mode nodes recurse: their children are composed using the parent's
placed bbox as the nested glyph_bbox.
"""

from __future__ import annotations

from dataclasses import replace

from olik_font.constraints.presets import (
    apply_enclose,
    apply_left_right,
    apply_repeat_triangle,
    apply_top_bottom,
)
from olik_font.constraints.primitives import Primitive
from olik_font.geom import apply_affine_to_point
from olik_font.types import Affine, BBox, InstancePlacement


def compose_transforms(
    node: InstancePlacement,
    glyph_bbox: BBox,
) -> tuple[InstancePlacement, tuple[Primitive, ...]]:
    """Resolve all descendant transforms. Returns (new_root, resolved_constraints)."""
    if not node.children:
        return node, ()

    adapter = node.input_adapter
    children = node.children
    resolved_children: tuple[InstancePlacement, ...]
    local_constraints: tuple[Primitive, ...]

    if adapter == "preset:left_right":
        assert len(children) == 2, "left_right expects 2 children"
        left_child, right_child, cs = apply_left_right(children[0], children[1], glyph_bbox)
        resolved_children = (left_child, right_child)
        local_constraints = cs
    elif adapter == "preset:top_bottom":
        assert len(children) == 2, "top_bottom expects 2 children"
        t, b, cs = apply_top_bottom(children[0], children[1], glyph_bbox)
        resolved_children = (t, b)
        local_constraints = cs
    elif adapter == "preset:enclose":
        assert len(children) == 2, "enclose expects 2 children"
        o, i, cs = apply_enclose(children[0], children[1], glyph_bbox)
        resolved_children = (o, i)
        local_constraints = cs
    elif adapter == "direct:repeat_triangle":
        assert len(children) == 3, "repeat_triangle expects 3 children"
        resolved, cs = apply_repeat_triangle(
            (children[0], children[1], children[2]),
            glyph_bbox,
        )
        resolved_children = resolved
        local_constraints = cs
    else:
        # "direct" / "leaf" / unknown -> identity at this level
        resolved_children = children
        local_constraints = ()

    descendant_constraints: list[Primitive] = []
    final_children: list[InstancePlacement] = []
    for child in resolved_children:
        if child.children:
            child_bbox = _placed_bbox(child.transform)
            new_child, child_cs = compose_transforms(child, child_bbox)
            final_children.append(new_child)
            descendant_constraints.extend(child_cs)
        else:
            final_children.append(child)

    return (
        replace(node, children=tuple(final_children)),
        local_constraints + tuple(descendant_constraints),
    )


def _placed_bbox(transform: Affine) -> BBox:
    """Recover axis-aligned bbox by applying transform to canonical corners."""
    p0 = apply_affine_to_point(transform, (0.0, 0.0))
    p1 = apply_affine_to_point(transform, (1024.0, 1024.0))
    x0, x1 = sorted((p0[0], p1[0]))
    y0, y1 = sorted((p0[1], p1[1]))
    return (x0, y0, x1, y1)
