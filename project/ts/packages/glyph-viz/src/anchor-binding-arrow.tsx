import * as React from "react";
import type { Point } from "@olik/glyph-schema";

export interface AnchorBindingArrowProps {
  from: Point;
  to: Point;
  color?: string;
  label?: string;
}

export function AnchorBindingArrow({
  from,
  to,
  color = "#f59e0b",
  label,
}: AnchorBindingArrowProps): React.ReactElement {
  const [x0, y0] = from;
  const [x1, y1] = to;
  const id = `arrowhead-${Math.floor((x0 + y0 + x1 + y1) * 1000)}`;
  const midX = (x0 + x1) / 2;
  const midY = (y0 + y1) / 2;
  return (
    <g className="olik-anchor-binding">
      <defs>
        <marker
          id={id}
          viewBox="0 0 10 10"
          refX="8"
          refY="5"
          markerWidth="8"
          markerHeight="8"
          orient="auto"
        >
          <path d="M 0 0 L 10 5 L 0 10 z" fill={color} />
        </marker>
      </defs>
      <line
        x1={x0}
        y1={y0}
        x2={x1}
        y2={y1}
        stroke={color}
        strokeWidth={2}
        markerEnd={`url(#${id})`}
      />
      {label ? (
        <text x={midX} y={midY - 6} fontSize={11} fontFamily="monospace" fill={color}>
          {label}
        </text>
      ) : null}
    </g>
  );
}
