import * as React from "react";

export interface VirtualCoordGridProps {
  size?: number;
  majorStep?: number;
  minorStep?: number;
  majorColor?: string;
  minorColor?: string;
}

export function VirtualCoordGrid({
  size = 1024,
  majorStep = 128,
  minorStep = 32,
  majorColor = "#cbd5e1",
  minorColor = "#eef2ff",
}: VirtualCoordGridProps): React.ReactElement {
  const minorLines: React.ReactElement[] = [];
  for (let x = minorStep; x < size; x += minorStep) {
    if (x % majorStep === 0) continue;
    minorLines.push(
      <line key={`mv${x}`} x1={x} y1={0} x2={x} y2={size} stroke={minorColor} strokeWidth={1} />,
    );
    minorLines.push(
      <line key={`mh${x}`} x1={0} y1={x} x2={size} y2={x} stroke={minorColor} strokeWidth={1} />,
    );
  }
  const majorLines: React.ReactElement[] = [];
  for (let x = 0; x <= size; x += majorStep) {
    majorLines.push(
      <line key={`Mv${x}`} x1={x} y1={0} x2={x} y2={size} stroke={majorColor} strokeWidth={1} />,
    );
    majorLines.push(
      <line key={`Mh${x}`} x1={0} y1={x} x2={size} y2={x} stroke={majorColor} strokeWidth={1} />,
    );
  }
  return (
    <g className="olik-virtual-coord-grid">
      {minorLines}
      {majorLines}
      <rect x={0} y={0} width={size} height={size} fill="none" stroke={majorColor} strokeWidth={2} />
    </g>
  );
}
