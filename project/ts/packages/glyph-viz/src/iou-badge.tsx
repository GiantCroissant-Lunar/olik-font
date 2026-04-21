import * as React from "react";
import { iouColor } from "./theme.js";

export interface IoUBadgeProps {
  value: number;
  label?: string;
  x?: number;
  y?: number;
}

export function IoUBadge({
  value, label, x = 0, y = 0,
}: IoUBadgeProps): React.ReactElement {
  const text = label ?? `IoU ${value.toFixed(2)}`;
  const color = iouColor(value);

  return (
    <g className="olik-iou-badge" transform={`translate(${x}, ${y})`}>
      <rect x={0} y={0} width={72} height={20} rx={4} fill={color} />
      <text x={36} y={14} fontSize={11} fontFamily="monospace" fill="#fff" textAnchor="middle">
        {text}
      </text>
    </g>
  );
}
