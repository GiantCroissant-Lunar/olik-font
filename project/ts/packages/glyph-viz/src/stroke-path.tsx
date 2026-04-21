import * as React from "react";
import { STROKE_COLOR } from "./theme.js";

export interface StrokePathProps {
  outlinePath: string;
  median: ReadonlyArray<readonly [number, number]>;
  progress: number;
  strokeWidth?: number;
  className?: string;
}

export function StrokePath({
  outlinePath,
  median,
  progress,
  strokeWidth = 48,
  className,
}: StrokePathProps): React.ReactElement {
  const medianD = medianToPath(median);
  const totalLen = medianLength(median);
  const drawn = Math.max(0, Math.min(1, progress)) * totalLen;
  const dashArray = totalLen > 0 ? `${totalLen} ${totalLen}` : "0 0";
  const dashOffset = totalLen - drawn;

  return (
    <g className={className}>
      <path d={outlinePath} fill={STROKE_COLOR.outline} fillOpacity={0.25} />
      <path
        d={medianD}
        fill="none"
        stroke={STROKE_COLOR.median}
        strokeWidth={strokeWidth}
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeDasharray={dashArray}
        strokeDashoffset={dashOffset}
      />
    </g>
  );
}

function medianToPath(median: ReadonlyArray<readonly [number, number]>): string {
  if (median.length === 0) return "M 0 0 Z";
  const [[x0, y0], ...rest] = median;
  return `M ${x0} ${y0} ${rest.map(([x, y]) => `L ${x} ${y}`).join(" ")}`;
}

function medianLength(median: ReadonlyArray<readonly [number, number]>): number {
  let total = 0;
  for (let i = 1; i < median.length; i++) {
    const [x0, y0] = median[i - 1]!;
    const [x1, y1] = median[i]!;
    total += Math.hypot(x1 - x0, y1 - y0);
  }
  return total;
}
