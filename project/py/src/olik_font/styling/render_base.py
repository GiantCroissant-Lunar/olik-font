"""Render glyph-record stroke geometry to a black-on-white PNG."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw
from svgpathtools import Path as SvgPath
from svgpathtools import parse_path

_MEDIAN_STROKE_WIDTH = 48.0


def render_base_png(glyph_record: dict[str, Any], dest: Path, size: int = 1024) -> Path:
    """Render a glyph record to a square PNG for ComfyUI control input."""
    if size <= 0:
        raise ValueError("size must be positive")

    coord_space = glyph_record.get("coord_space")
    if not isinstance(coord_space, dict):
        raise ValueError("glyph_record missing coord_space")
    width = _as_positive_float(coord_space.get("width"), field="coord_space.width")
    height = _as_positive_float(coord_space.get("height"), field="coord_space.height")

    strokes = glyph_record.get("stroke_instances")
    if not isinstance(strokes, list):
        raise ValueError("glyph_record missing stroke_instances")

    dest.parent.mkdir(parents=True, exist_ok=True)

    svg = _build_svg(strokes, width=width, height=height, size=size)
    if _render_with_cairosvg(svg, dest, size=size):
        return dest

    image = Image.new("L", (size, size), color=255)
    draw = ImageDraw.Draw(image)
    for stroke in strokes:
        _draw_stroke(
            draw,
            stroke,
            width=width,
            height=height,
            pixel_size=size,
        )
    image.save(dest, format="PNG")
    return dest


def _build_svg(strokes: Sequence[dict[str, Any]], *, width: float, height: float, size: int) -> str:
    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        (
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'width="{size}" height="{size}" viewBox="0 0 {width:g} {height:g}">'
        ),
        f'<rect x="0" y="0" width="{width:g}" height="{height:g}" fill="#ffffff"/>',
        f'<g transform="translate(0,{height:g}) scale(1,-1)">',
    ]
    stroke_width = _MEDIAN_STROKE_WIDTH
    for stroke in strokes:
        path_d = _require_str(stroke.get("path"), field="stroke.path")
        parts.append(f'<path d="{path_d}" fill="#000000" stroke="none"/>')
        median = _median_path(stroke.get("median"))
        if median is not None:
            parts.append(
                '<path d="'
                + median
                + f'" fill="none" stroke="#000000" stroke-width="{stroke_width:g}"'
                ' stroke-linecap="round" stroke-linejoin="round"/>'
            )
    parts.append("</g></svg>")
    return "".join(parts)


def _render_with_cairosvg(svg: str, dest: Path, *, size: int) -> bool:
    try:
        import cairosvg
    except ImportError:
        return False

    cairosvg.svg2png(
        bytestring=svg.encode("utf-8"),
        write_to=str(dest),
        output_width=size,
        output_height=size,
    )
    return True


def _draw_stroke(
    draw: ImageDraw.ImageDraw,
    stroke: dict[str, Any],
    *,
    width: float,
    height: float,
    pixel_size: int,
) -> None:
    path_d = _require_str(stroke.get("path"), field="stroke.path")
    path = parse_path(path_d)
    outline = _sample_path(path)
    if outline and _is_closed_path(path_d, path):
        draw.polygon(
            [
                _to_image_point(point, width=width, height=height, pixel_size=pixel_size)
                for point in outline
            ],
            fill=0,
        )

    median = _median_points(stroke.get("median"))
    if len(median) >= 2:
        draw.line(
            [
                _to_image_point(point, width=width, height=height, pixel_size=pixel_size)
                for point in median
            ],
            fill=0,
            width=max(1, round(_MEDIAN_STROKE_WIDTH * pixel_size / max(width, height))),
            joint="curve",
        )


def _sample_path(path: SvgPath) -> list[tuple[float, float]]:
    points: list[tuple[float, float]] = []
    for segment in path:
        length = segment.length(error=1e-4)
        steps = max(1, int(length / 8))
        for step in range(steps):
            point = segment.point(step / steps)
            _append_point(points, point.real, point.imag)
        endpoint = segment.point(1.0)
        _append_point(points, endpoint.real, endpoint.imag)
    return points


def _append_point(points: list[tuple[float, float]], x: float, y: float) -> None:
    candidate = (float(x), float(y))
    if not points or points[-1] != candidate:
        points.append(candidate)


def _is_closed_path(path_d: str, path: SvgPath) -> bool:
    if path_d.rstrip().lower().endswith("z"):
        return True
    if not path:
        return False
    start = path[0].start
    end = path[-1].end
    return abs(start.real - end.real) < 1e-6 and abs(start.imag - end.imag) < 1e-6


def _median_points(raw: Any) -> tuple[tuple[float, float], ...]:
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        return ()
    points: list[tuple[float, float]] = []
    for point in raw:
        if not isinstance(point, Sequence) or len(point) != 2:
            continue
        points.append((float(point[0]), float(point[1])))
    return tuple(points)


def _median_path(raw: Any) -> str | None:
    points = _median_points(raw)
    if len(points) < 2:
        return None
    start = f"M {points[0][0]:g} {points[0][1]:g}"
    rest = " ".join(f"L {x:g} {y:g}" for x, y in points[1:])
    return f"{start} {rest}"


def _to_image_point(
    point: tuple[float, float], *, width: float, height: float, pixel_size: int
) -> tuple[float, float]:
    x, y = point
    px = min(pixel_size - 1, max(0.0, x * pixel_size / width))
    py = min(pixel_size - 1, max(0.0, (height - y) * pixel_size / height))
    return (px, py)


def _require_str(value: Any, *, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field} must be a non-empty string")
    return value


def _as_positive_float(value: Any, *, field: str) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be numeric") from exc
    if parsed <= 0:
        raise ValueError(f"{field} must be positive")
    return parsed
