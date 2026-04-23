"""Post-order walk over InstancePlacement trees; fills in measured transforms."""

from __future__ import annotations

from dataclasses import replace
from functools import cache
from pathlib import Path
from typing import Protocol

from olik_font.constraints.primitives import Primitive
from olik_font.geom import bbox_to_bbox_affine, union_bbox
from olik_font.prototypes.measure import CANONICAL, measure_instance_transform
from olik_font.sources.makemeahanzi import load_mmh_graphics
from olik_font.types import Affine, BBox, InstancePlacement

_PY_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_MMH_GRAPHICS = _PY_ROOT / "data" / "mmh" / "graphics.txt"


class MmhLookup(Protocol):
    def __call__(self, char: str) -> tuple[str, ...]: ...


class UnderspecifiedPlacement(ValueError):  # noqa: N818
    """Raised when compose cannot infer a node's measured placement."""


@cache
def _default_mmh_chars():
    return load_mmh_graphics(_DEFAULT_MMH_GRAPHICS)


def _default_mmh_lookup(char: str) -> tuple[str, ...]:
    try:
        return tuple(_default_mmh_chars()[char].strokes)
    except KeyError as exc:
        raise KeyError(f"missing MMH glyph for {char}") from exc


MMH_LOOKUP: MmhLookup = _default_mmh_lookup


def compose_transforms(
    node: InstancePlacement,
    glyph_bbox: BBox,
) -> tuple[InstancePlacement, tuple[Primitive, ...]]:
    """Resolve all descendant transforms from measured MMH geometry."""
    root_char = _root_char(node)
    resolved = _compose_node(node, root_char=root_char, glyph_bbox=glyph_bbox, is_root=True)
    return resolved, ()


def _compose_node(
    node: InstancePlacement,
    *,
    root_char: str,
    glyph_bbox: BBox,
    is_root: bool = False,
) -> InstancePlacement:
    resolved_children = tuple(
        _compose_node(child, root_char=root_char, glyph_bbox=glyph_bbox) for child in node.children
    )
    transform = _resolve_transform(
        node,
        children=resolved_children,
        root_char=root_char,
        glyph_bbox=glyph_bbox,
        is_root=is_root,
    )
    return replace(node, transform=transform, children=resolved_children)


def _resolve_transform(
    node: InstancePlacement,
    *,
    children: tuple[InstancePlacement, ...],
    root_char: str,
    glyph_bbox: BBox,
    is_root: bool,
) -> Affine:
    if is_root:
        if node.transform is not None:
            return node.transform
        return bbox_to_bbox_affine(CANONICAL, glyph_bbox)

    if node.transform is not None:
        return node.transform

    if node.mode in {"keep", "replace"} and node.source_stroke_indices:
        return measure_instance_transform(_stroke_paths(root_char, node.source_stroke_indices))

    if node.mode == "refine" and children:
        return bbox_to_bbox_affine(
            CANONICAL,
            union_bbox(tuple(_placed_bbox(child.transform) for child in children)),
        )

    raise UnderspecifiedPlacement(node.instance_id)


def _stroke_paths(char: str, indices: tuple[int, ...]) -> tuple[str, ...]:
    strokes = MMH_LOOKUP(char)
    try:
        return tuple(strokes[i] for i in indices)
    except IndexError as exc:
        raise ValueError(f"{char}: invalid stroke indices {indices}") from exc


def _root_char(node: InstancePlacement) -> str:
    char = node.decomp_source.get("char")
    if not isinstance(char, str) or not char:
        raise ValueError("compose root missing decomp_source.char")
    return char


def _placed_bbox(transform: Affine | None) -> BBox:
    if transform is None:
        raise ValueError("compose requires transforms before placed-bbox recovery")
    tx, ty = transform.translate
    sx, sy = transform.scale
    return (tx, ty, tx + 1024.0 * sx, ty + 1024.0 * sy)
