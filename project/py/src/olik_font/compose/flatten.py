"""Flatten a composed InstancePlacement tree to a list of StrokeInstance records.

A leaf is any placement whose prototype_ref resolves in the library AND has
no children. Refine intermediates (children + prototype_ref like proto:__glyph_*
or any missing-from-library ref) contribute no strokes directly — only their
descendant leaves do.
"""

from __future__ import annotations

from dataclasses import dataclass

from olik_font.compose.z_layers import z_for_stroke
from olik_font.geom import apply_affine_to_median, apply_affine_to_path, bbox_of_paths
from olik_font.types import Affine, BBox, InstancePlacement, Point, PrototypeLibrary


@dataclass(frozen=True, slots=True)
class StrokeInstance:
    id: str
    instance_id: str
    order: int
    path: str
    median: tuple[Point, ...]
    bbox: BBox
    z: int
    role: str


def flatten_strokes(
    root: InstancePlacement,
    library: PrototypeLibrary,
) -> tuple[StrokeInstance, ...]:
    out: list[StrokeInstance] = []
    counter = {"n": 0}
    _visit(root, Affine.identity(), library, out, counter)
    return tuple(out)


def _visit(
    node: InstancePlacement,
    outer: Affine,
    library: PrototypeLibrary,
    out: list[StrokeInstance],
    counter: dict[str, int],
) -> None:
    from olik_font.geom import affine_compose

    cumulative = affine_compose(outer, node.transform)

    if node.children:
        for child in node.children:
            _visit(child, cumulative, library, out, counter)
        return

    if not library.contains(node.prototype_ref):
        return

    proto = library[node.prototype_ref]
    for stroke in proto.strokes:
        new_path = apply_affine_to_path(cumulative, stroke.path)
        new_median = apply_affine_to_median(cumulative, stroke.median)
        new_bbox = bbox_of_paths([new_path])
        z = z_for_stroke(stroke.role, stroke.order)
        counter["n"] += 1
        out.append(
            StrokeInstance(
                id=f"si{counter['n']:04d}",
                instance_id=node.instance_id,
                order=stroke.order,
                path=new_path,
                median=new_median,
                bbox=new_bbox,
                z=z,
                role=stroke.role,
            )
        )
