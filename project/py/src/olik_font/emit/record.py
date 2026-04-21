"""Serialize a composed InstancePlacement tree -> glyph-record.schema.json shape."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from functools import cache

from olik_font.compose.flatten import flatten_strokes
from olik_font.compose.iou import iou_report_for
from olik_font.constraints.primitives import Primitive
from olik_font.constraints.primitives import as_dict as primitive_to_dict
from olik_font.geom import (
    apply_affine_to_path,
    apply_affine_to_point,
    bbox_of_paths,
    bbox_to_bbox_affine,
    normalize_paths_to_canonical,
)
from olik_font.sources.makemeahanzi import MmhChar
from olik_font.types import Affine, BBox, InstancePlacement, PrototypeLibrary

_UNICODE = {
    "明": "U+660E",
    "清": "U+6E05",
    "國": "U+570B",
    "森": "U+68EE",
}

_RENDER_LAYERS = [
    {"name": "skeleton", "z_min": 0, "z_max": 9},
    {"name": "stroke_body", "z_min": 10, "z_max": 49},
    {"name": "stroke_edge", "z_min": 50, "z_max": 69},
    {"name": "texture_overlay", "z_min": 70, "z_max": 89},
    {"name": "damage", "z_min": 90, "z_max": 99},
]

_PROTO_REF_RE = re.compile(r"^proto:[A-Za-z0-9_]+$")


def build_glyph_record(
    char: str,
    resolved_tree: InstancePlacement,
    constraints: tuple[Primitive, ...],
    library: PrototypeLibrary,
    mmh_char: MmhChar,
) -> dict:
    strokes = flatten_strokes(resolved_tree, library)

    iou = _build_iou_report(strokes, mmh_char)

    return {
        "schema_version": "0.1",
        "glyph_id": char,
        "unicode": _UNICODE.get(char, "U+0000"),
        "coord_space": {"width": 1024, "height": 1024, "origin": "top-left", "y_axis": "down"},
        "source": {"stroke_source": "make-me-a-hanzi", "decomp_source": "cjk-decomp"},
        "layout_tree": _node_to_dict(resolved_tree),
        "component_instances": [
            {
                "id": inst.instance_id,
                "prototype_ref": inst.prototype_ref,
                "transform": _affine_to_dict(inst.transform),
                "placed_bbox": list(_placed_bbox(inst.transform)),
            }
            for inst in _leaves_with_library(resolved_tree, library)
        ],
        "stroke_instances": [
            {
                "id": s.id,
                "instance_id": s.instance_id,
                "order": s.order,
                "path": s.path,
                "median": [list(p) for p in s.median],
                "bbox": list(s.bbox),
                "z": s.z,
                "role": s.role,
            }
            for s in strokes
        ],
        "constraints": [primitive_to_dict(c) for c in constraints],
        "render_layers": _RENDER_LAYERS,
        "roles": _roles_for(resolved_tree, library),
        "metadata": {
            "generated_at": datetime.now(UTC).isoformat(),
            "generator": "olik-font py/0.1",
            "iou_report": iou,
        },
    }


def _affine_to_dict(a: Affine) -> dict:
    return {
        "translate": list(a.translate),
        "scale": list(a.scale),
        "rotate": a.rotate,
        "shear": list(a.shear),
    }


def _placed_bbox(a: Affine) -> BBox:
    p0 = apply_affine_to_point(a, (0.0, 0.0))
    p1 = apply_affine_to_point(a, (1024.0, 1024.0))
    x0, x1 = sorted((p0[0], p1[0]))
    y0, y1 = sorted((p0[1], p1[1]))
    return (x0, y0, x1, y1)


def _node_to_dict(n: InstancePlacement) -> dict:
    d: dict = {
        "id": n.instance_id,
        "bbox": list(_placed_bbox(n.transform)),
        "mode": n.mode,
        "depth": n.depth,
        "transform": _affine_to_dict(n.transform),
        "input_adapter": n.input_adapter,
        "children": [_node_to_dict(c) for c in n.children],
    }
    if _PROTO_REF_RE.match(n.prototype_ref):
        d["prototype_ref"] = n.prototype_ref
    if n.anchor_bindings:
        d["anchor_bindings"] = [
            {
                "from": ab.from_,
                "to": ab.to,
                **({"distance": ab.distance} if ab.distance is not None else {}),
            }
            for ab in n.anchor_bindings
        ]
    if n.decomp_source:
        d["decomp_source"] = dict(n.decomp_source)
    return d


def _leaves_with_library(
    node: InstancePlacement, library: PrototypeLibrary
) -> list[InstancePlacement]:
    if node.children:
        out: list[InstancePlacement] = []
        for c in node.children:
            out.extend(_leaves_with_library(c, library))
        return out
    return [node] if library.contains(node.prototype_ref) else []


def _roles_for(node: InstancePlacement, library: PrototypeLibrary) -> dict:
    roles: dict[str, dict] = {}
    for leaf in _leaves_with_library(node, library):
        proto = library[leaf.prototype_ref]
        if proto.roles:
            roles[leaf.instance_id] = {"dong_chinese": proto.roles[0]}
    return roles


def _build_iou_report(strokes, mmh_char: MmhChar) -> dict:
    composed_bboxes = tuple(s.bbox for s in strokes)
    if len(composed_bboxes) != len(mmh_char.strokes):
        return {
            "mean": 0.0,
            "min": 0.0,
            "per_stroke": {},
            "note": f"stroke count mismatch: composed={len(composed_bboxes)} mmh={len(mmh_char.strokes)}",
        }

    mmh_paths, _ = normalize_paths_to_canonical(tuple(mmh_char.strokes), (0, 0, 1024, 1024))
    per_stroke: dict[str, float] = {}
    values: list[float] = []
    offset = 0
    for group in _stroke_groups_by_instance(strokes):
        window_scores = _best_window_scores(group, mmh_paths)
        for score in window_scores:
            per_stroke[f"s{offset}"] = score
            values.append(score)
            offset += 1
    return {
        "mean": sum(values) / len(values),
        "min": min(values),
        "per_stroke": per_stroke,
    }


def _stroke_groups_by_instance(strokes) -> tuple[tuple, ...]:
    grouped: list[list] = []
    current_id: str | None = None
    current: list = []
    for stroke in strokes:
        if stroke.instance_id != current_id:
            if current:
                grouped.append(current)
            current_id = stroke.instance_id
            current = [stroke]
        else:
            current.append(stroke)
    if current:
        grouped.append(current)
    return tuple(tuple(group) for group in grouped)


def _best_window_scores(group, mmh_paths: tuple[str, ...]) -> tuple[float, ...]:
    group_paths = tuple(stroke.path for stroke in group)
    n = len(group_paths)
    best: tuple[float, float, tuple[float, ...]] | None = None
    for start in range(len(mmh_paths) - n + 1):
        window = tuple(mmh_paths[start : start + n])
        affine = bbox_to_bbox_affine(bbox_of_paths(group_paths), bbox_of_paths(window))
        aligned = tuple(apply_affine_to_path(affine, path) for path in group_paths)
        scores = _optimal_bbox_scores(aligned, window)
        candidate = (sum(scores) / len(scores), min(scores), scores)
        if best is None or candidate[:2] > best[:2]:
            best = candidate
    assert best is not None
    return best[2]


def _optimal_bbox_scores(
    composed_paths: tuple[str, ...],
    mmh_paths: tuple[str, ...],
) -> tuple[float, ...]:
    composed_bboxes = tuple(bbox_of_paths([path]) for path in composed_paths)
    mmh_bboxes = tuple(bbox_of_paths([path]) for path in mmh_paths)
    n = len(composed_bboxes)
    if n == 0:
        return ()

    matrix = tuple(
        tuple(float(iou_report_for([composed], [target])["mean"]) for target in mmh_bboxes)
        for composed in composed_bboxes
    )

    @cache
    def _best(i: int, mask: int) -> tuple[float, tuple[int, ...]]:
        if i == n:
            return 0.0, ()

        best_total = -1.0
        best_assign: tuple[int, ...] = ()
        for j in range(n):
            if not mask & (1 << j):
                continue
            rest_total, rest_assign = _best(i + 1, mask ^ (1 << j))
            total = matrix[i][j] + rest_total
            if total > best_total:
                best_total = total
                best_assign = (j, *rest_assign)
        return best_total, best_assign

    _, assignment = _best(0, (1 << n) - 1)
    return tuple(matrix[i][j] for i, j in enumerate(assignment))
