"""Affine math + SVG-path bbox helpers.

Affine is stored in parameter form (translate/scale/rotate/shear) and
compiled to a 2x3 matrix only at application time. This keeps records
JSON-round-trippable without matrix normalization issues.
"""

from __future__ import annotations

import math
import re

from svgpathtools import parse_path

from olik_font.types import Affine, BBox, Point

_PATH_COORD_RE = re.compile(r"-?\d+(?:\.\d+)?")


def _compile(a: Affine) -> tuple[float, float, float, float, float, float]:
    """Compile Affine → 2x3 matrix rows (m00, m01, m02, m10, m11, m12)."""
    sx, sy = a.scale
    kx, ky = a.shear
    cos = math.cos(a.rotate)
    sin = math.sin(a.rotate)
    # matrix = translate · rotate · shear · scale
    # shear matrix = [[1, kx],[ky, 1]]
    # combined linear part L = R · S · D (where D = shear · scale)
    # we apply scale first, then shear, then rotate, then translate.
    m00 = cos * sx + -sin * (ky * sx)
    m01 = cos * (kx * sy) + -sin * sy
    m10 = sin * sx + cos * (ky * sx)
    m11 = sin * (kx * sy) + cos * sy
    m02 = a.translate[0]
    m12 = a.translate[1]
    return m00, m01, m02, m10, m11, m12


def apply_affine_to_point(a: Affine, p: Point) -> Point:
    m00, m01, m02, m10, m11, m12 = _compile(a)
    x = m00 * p[0] + m01 * p[1] + m02
    y = m10 * p[0] + m11 * p[1] + m12
    return (x, y)


def apply_affine_to_median(a: Affine, med: tuple[Point, ...]) -> tuple[Point, ...]:
    return tuple(apply_affine_to_point(a, p) for p in med)


def affine_compose(outer: Affine, inner: Affine) -> Affine:
    """Return affine equivalent to: apply inner, then outer.

    Non-commuting composition: we round-trip via matrix form then back.
    """
    om = _compile(outer)
    im = _compile(inner)
    # result = O · I
    m00 = om[0] * im[0] + om[1] * im[3]
    m01 = om[0] * im[1] + om[1] * im[4]
    m02 = om[0] * im[2] + om[1] * im[5] + om[2]
    m10 = om[3] * im[0] + om[4] * im[3]
    m11 = om[3] * im[1] + om[4] * im[4]
    m12 = om[3] * im[2] + om[4] * im[5] + om[5]
    # decompose matrix → translate/scale/rotate/shear
    # (rotate = 0 case covers the bulk of our uses; full polar decomposition follows)
    tx, ty = m02, m12
    sx = math.hypot(m00, m10)
    sy = math.hypot(m01, m11)
    rotate = math.atan2(m10, m00)
    cos_r = math.cos(-rotate)
    sin_r = math.sin(-rotate)
    shear_num = cos_r * m01 - sin_r * m11
    shear_kx = shear_num / sy if sy else 0.0
    return Affine(translate=(tx, ty), scale=(sx, sy), rotate=rotate, shear=(shear_kx, 0.0))


def apply_affine_to_path(a: Affine, path_d: str) -> str:
    """Apply affine to every coordinate pair in an SVG path d-string.

    Assumes absolute commands (M/L/C/Q/Z) with raw x,y pairs. Seed MMH strokes
    are already absolute + flat — tightening parser scope to absolute-only
    keeps this simple and deterministic.
    """
    out: list[str] = []
    tokens = re.findall(r"[A-Za-z]|-?\d+(?:\.\d+)?", path_d)
    i = 0
    while i < len(tokens):
        cmd = tokens[i]
        if cmd.isalpha():
            out.append(cmd)
            i += 1
            # collect following coordinate pairs until next alpha token
            while i + 1 < len(tokens) and not tokens[i].isalpha() and not tokens[i + 1].isalpha():
                x = float(tokens[i])
                y = float(tokens[i + 1])
                nx, ny = apply_affine_to_point(a, (x, y))
                out.append(_fmt(nx))
                out.append(_fmt(ny))
                i += 2
            # trailing single numeric (e.g. h/v) — keep as-is (MMH uses L/M/Z only)
            while i < len(tokens) and not tokens[i].isalpha():
                out.append(tokens[i])
                i += 1
        else:
            out.append(tokens[i])
            i += 1
    return " ".join(out)


def _fmt(v: float) -> str:
    if v == int(v):
        return str(int(v))
    return f"{v:.3f}".rstrip("0").rstrip(".")


def bbox_of_paths(paths: list[str] | tuple[str, ...]) -> BBox:
    xmin = ymin = float("inf")
    xmax = ymax = float("-inf")
    for d in paths:
        p = parse_path(d)
        b = p.bbox()  # (xmin, xmax, ymin, ymax)
        xmin = min(xmin, b[0])
        xmax = max(xmax, b[1])
        ymin = min(ymin, b[2])
        ymax = max(ymax, b[3])
    return (xmin, ymin, xmax, ymax)


def union_bbox(bboxes: tuple[BBox, ...]) -> BBox:
    xs0 = min(b[0] for b in bboxes)
    ys0 = min(b[1] for b in bboxes)
    xs1 = max(b[2] for b in bboxes)
    ys1 = max(b[3] for b in bboxes)
    return (xs0, ys0, xs1, ys1)


def bbox_to_bbox_affine(src: BBox, dst: BBox) -> Affine:
    """Affine that maps src bbox corners onto dst bbox corners (axis-aligned)."""
    sx = (dst[2] - dst[0]) / (src[2] - src[0])
    sy = (dst[3] - dst[1]) / (src[3] - src[1])
    tx = dst[0] - src[0] * sx
    ty = dst[1] - src[1] * sy
    return Affine(translate=(tx, ty), scale=(sx, sy))


def normalize_paths_to_canonical(
    paths: list[str] | tuple[str, ...],
    canonical_bbox: BBox,
) -> tuple[tuple[str, ...], Affine]:
    """Rescale `paths` so their union bbox maps to `canonical_bbox`.

    Returns (normalized_paths, forward_affine). forward_affine maps points
    in the original (MMH) coord space to canonical space.
    """
    src = bbox_of_paths(list(paths))
    fwd = bbox_to_bbox_affine(src, canonical_bbox)
    normalized = tuple(apply_affine_to_path(fwd, d) for d in paths)
    return normalized, fwd


def fit_in_slot(
    src: BBox,
    dst: BBox,
    anchor: str,
) -> BBox:
    """Return the sub-bbox of `dst` preserving `src`'s aspect ratio,
    anchored at the named position within `dst`.

    Used by Plan 10.1's preset adapters to stop non-uniform slot
    stretching. The caller then passes the returned bbox to
    `bbox_to_bbox_affine(src, result)`, which produces a uniform-scale
    affine (because aspect(src) == aspect(result) by construction).

    y-up convention: `dst[3]` is the visual top; `dst[1]` is the
    visual bottom. Anchor names describe visual position:

    - `top-left`: left edge + top edge of dst
    - `top-center`: x-centered + top edge of dst
    - `bottom-center`: x-centered + bottom edge of dst
    - `center`: centered on both axes

    Raises ValueError for zero-area `src` or unknown anchor.
    """
    sw = src[2] - src[0]
    sh = src[3] - src[1]
    if sw <= 0 or sh <= 0:
        raise ValueError(f"src bbox has zero area: {src}")

    dw = dst[2] - dst[0]
    dh = dst[3] - dst[1]
    if dw <= 0 or dh <= 0:
        return dst

    scale = min(dw / sw, dh / sh)
    new_w = sw * scale
    new_h = sh * scale

    cx = (dst[0] + dst[2]) / 2.0
    cy = (dst[1] + dst[3]) / 2.0

    if anchor == "top-left":
        x0 = dst[0]
        x1 = x0 + new_w
        y1 = dst[3]
        y0 = y1 - new_h
    elif anchor == "top-center":
        x0 = cx - new_w / 2.0
        x1 = cx + new_w / 2.0
        y1 = dst[3]
        y0 = y1 - new_h
    elif anchor == "bottom-center":
        x0 = cx - new_w / 2.0
        x1 = cx + new_w / 2.0
        y0 = dst[1]
        y1 = y0 + new_h
    elif anchor == "center":
        x0 = cx - new_w / 2.0
        x1 = cx + new_w / 2.0
        y0 = cy - new_h / 2.0
        y1 = cy + new_h / 2.0
    else:
        raise ValueError(f"unknown anchor: {anchor!r}")

    return (x0, y0, x1, y1)
