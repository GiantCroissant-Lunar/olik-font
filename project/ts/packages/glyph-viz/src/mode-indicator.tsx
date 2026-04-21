import * as React from "react";

const SYMBOL: Record<string, string> = {
  keep: "○",
  refine: "◐",
  replace: "●",
};

export interface ModeIndicatorProps {
  mode: "keep" | "refine" | "replace";
  x?: number;
  y?: number;
}

export function ModeIndicator({
  mode, x = 0, y = 0,
}: ModeIndicatorProps): React.ReactElement {
  return (
    <g className="olik-mode-indicator" transform={`translate(${x}, ${y})`}>
      <text x={0} y={12} fontSize={14} fontFamily="monospace">
        {SYMBOL[mode]} {mode}
      </text>
    </g>
  );
}
