import * as React from "react";
import { INPUT_ADAPTER_COLOR } from "./theme.js";

export interface InputAdapterChipProps {
  adapter: string;
  x?: number;
  y?: number;
}

export function InputAdapterChip({
  adapter, x = 0, y = 0,
}: InputAdapterChipProps): React.ReactElement {
  const color = INPUT_ADAPTER_COLOR[adapter] ?? "#64748b";
  const text = adapter;

  return (
    <g className="olik-input-adapter-chip" transform={`translate(${x}, ${y})`}>
      <rect
        x={0}
        y={0}
        width={110}
        height={18}
        rx={3}
        fill={color}
        fillOpacity={0.15}
        stroke={color}
        strokeWidth={1}
      />
      <text x={6} y={13} fontSize={11} fontFamily="monospace" fill={color}>
        {text}
      </text>
    </g>
  );
}
