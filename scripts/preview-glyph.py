#!/usr/bin/env python3
"""Render a glyph-record JSON into a standalone SVG for eyeballing.

The SVG mirrors animCJK's style (grey stroke outlines + colored median
centerlines) so we can spot-check if the composed glyph actually looks
like the target character. Useful after running Plan 03's CLI when we
want a fast "did it work visually?" check.

Usage:
    python3 scripts/preview-glyph.py <glyph-record.json> [--out path]
    python3 scripts/preview-glyph.py project/schema/examples/glyph-record-明.json

Produces `<char>.svg` in CWD (or --out), then prints the absolute path
so a shell can pipe it to `open` on macOS.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SVG_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="480" height="480">
  <title>{char}</title>
  <rect x="0" y="0" width="{w}" height="{h}" fill="#ffffff" stroke="#e5e7eb" stroke-width="2"/>
  <!-- virtual coord grid (128-unit major ticks) -->
  <g stroke="#eef2ff" stroke-width="1" fill="none">
    {grid}
  </g>
  <!-- outline fills + median centerlines, animCJK idiom -->
  <g>
    {strokes}
  </g>
  <g font-family="monospace" font-size="28" fill="#64748b">
    <text x="12" y="32">{char}</text>
    <text x="12" y="{footer_y}">{n} strokes · iou mean {iou_mean} · min {iou_min}</text>
  </g>
</svg>
"""


def _grid_lines(w: int, h: int, step: int = 128) -> str:
    lines: list[str] = []
    for x in range(step, w, step):
        lines.append(f'<line x1="{x}" y1="0" x2="{x}" y2="{h}"/>')
    for y in range(step, h, step):
        lines.append(f'<line x1="0" y1="{y}" x2="{w}" y2="{y}"/>')
    return "\n    ".join(lines)


def _stroke_svg(strokes: list[dict]) -> str:
    parts: list[str] = []
    for s in strokes:
        # outline (fill) behind
        parts.append(
            f'<path d="{s["path"]}" fill="#1f2937" fill-opacity="0.2"/>'
        )
        # median centerline in front
        pts = s.get("median", [])
        if len(pts) >= 2:
            d = "M " + " L ".join(f"{p[0]} {p[1]}" for p in pts)
            parts.append(
                f'<path d="{d}" fill="none" stroke="#f97316" stroke-width="48"'
                ' stroke-linecap="round" stroke-linejoin="round"/>'
            )
    return "\n    ".join(parts)


def render(record_path: Path, out_path: Path | None = None) -> Path:
    record = json.loads(record_path.read_text(encoding="utf-8"))
    w = record["coord_space"]["width"]
    h = record["coord_space"]["height"]
    strokes = record["stroke_instances"]
    char = record.get("glyph_id", record_path.stem)
    iou = record.get("metadata", {}).get("iou_report") or {}
    iou_mean = f"{iou.get('mean', 0.0):.2f}" if "mean" in iou else "n/a"
    iou_min = f"{iou.get('min', 0.0):.2f}" if "min" in iou else "n/a"

    svg = SVG_TEMPLATE.format(
        w=w,
        h=h,
        char=char,
        grid=_grid_lines(w, h),
        strokes=_stroke_svg(strokes),
        footer_y=h - 12,
        n=len(strokes),
        iou_mean=iou_mean,
        iou_min=iou_min,
    )

    out = out_path or Path(f"{char}.svg")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(svg, encoding="utf-8")
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("record", type=Path, help="path to glyph-record-*.json")
    parser.add_argument("--out", type=Path, default=None, help="output svg path")
    args = parser.parse_args()

    if not args.record.exists():
        print(f"missing: {args.record}", file=sys.stderr)
        return 1

    out = render(args.record, args.out)
    print(out.resolve())
    return 0


if __name__ == "__main__":
    sys.exit(main())
