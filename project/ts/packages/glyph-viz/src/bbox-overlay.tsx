import * as React from "react";
import type { BBox } from "@olik/glyph-schema";

export interface BBoxOverlayProps {
  bbox: BBox;
  label?: string;
  color?: string;
  dashed?: boolean;
}

export function BBoxOverlay({
  bbox,
  label,
  color = "#0ea5e9",
  dashed = false,
}: BBoxOverlayProps): React.ReactElement {
  const [x0, y0, x1, y1] = bbox;
  const width = x1 - x0;
  const height = y1 - y0;
  return (
    <g className="olik-bbox">
      <rect
        x={x0}
        y={y0}
        width={width}
        height={height}
        fill="none"
        stroke={color}
        strokeWidth={2}
        strokeDasharray={dashed ? "8 4" : undefined}
      />
      {label ? (
        <text x={x0 + 6} y={y0 + 18} fill={color} fontSize={14} fontFamily="monospace">
          {label}
        </text>
      ) : null}
    </g>
  );
}
