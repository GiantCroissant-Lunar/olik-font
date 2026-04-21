"""Bounding-box IoU — pass-1 validator for composed strokes vs. MMH source.

Polygon-level IoU (shapely + path-to-polygon) is deferred; bbox IoU
captures placement and scale errors cheaply.
"""

from __future__ import annotations

from olik_font.types import BBox


def bbox_iou(a: BBox, b: BBox) -> float:
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    ix0 = max(ax0, bx0)
    iy0 = max(ay0, by0)
    ix1 = min(ax1, bx1)
    iy1 = min(ay1, by1)
    if ix1 <= ix0 or iy1 <= iy0:
        return 0.0
    inter = (ix1 - ix0) * (iy1 - iy0)
    area_a = (ax1 - ax0) * (ay1 - ay0)
    area_b = (bx1 - bx0) * (by1 - by0)
    return inter / (area_a + area_b - inter)


def iou_report_for(
    composed: list[BBox] | tuple[BBox, ...],
    mmh: list[BBox] | tuple[BBox, ...],
) -> dict:
    """Compute mean/min IoU + per-stroke scores.

    Pairing is positional: composed[i] vs mmh[i]. Length mismatch raises.
    """
    if len(composed) != len(mmh):
        raise ValueError(f"length mismatch: composed={len(composed)}, mmh={len(mmh)}")
    per: dict[str, float] = {}
    for i, (c, m) in enumerate(zip(composed, mmh, strict=False)):
        per[f"s{i}"] = bbox_iou(c, m)
    values = list(per.values()) or [1.0]
    return {
        "mean": sum(values) / len(values),
        "min": min(values),
        "per_stroke": per,
    }
