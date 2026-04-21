import * as React from "react";
import type { Point } from "@olik/glyph-schema";

export interface AnchorMarkerProps {
  name: string;
  point: Point;
  color?: string;
  radius?: number;
}

export function AnchorMarker({
  name,
  point,
  color = "#ec4899",
  radius = 6,
}: AnchorMarkerProps): React.ReactElement {
  const [x, y] = point;
  return (
    <g className="olik-anchor">
      <circle cx={x} cy={y} r={radius} fill={color} />
      <text x={x + radius + 4} y={y + 4} fontSize={11} fontFamily="monospace" fill={color}>
        {name}
      </text>
    </g>
  );
}
