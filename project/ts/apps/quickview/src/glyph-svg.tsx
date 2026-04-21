import * as React from "react";
import type { GlyphRecord } from "./types.js";

interface Props {
  record: GlyphRecord;
  size?: number;
}

export const GlyphSvg: React.FC<Props> = ({ record, size = 480 }) => {
  const w = record.coord_space.width;
  const h = record.coord_space.height;
  return (
    <svg
      viewBox={`0 0 ${w} ${h}`}
      width={size}
      height={size}
      style={{ background: "#ffffff", border: "1px solid #e5e7eb" }}
    >
      {/* virtual coord grid (128-unit major ticks) */}
      <g stroke="#eef2ff" strokeWidth={1} fill="none">
        {Array.from({ length: w / 128 - 1 }, (_, i) => 128 * (i + 1)).map((x) => (
          <line key={`v${x}`} x1={x} y1={0} x2={x} y2={h} />
        ))}
        {Array.from({ length: h / 128 - 1 }, (_, i) => 128 * (i + 1)).map((y) => (
          <line key={`h${y}`} x1={0} y1={y} x2={w} y2={y} />
        ))}
      </g>
      <g>
        {record.stroke_instances.map((s) => (
          <React.Fragment key={s.id}>
            {/* outline fill */}
            <path d={s.path} fill="#1f2937" fillOpacity={0.2} />
            {/* median centerline (animCJK idiom) */}
            {s.median.length >= 2 ? (
              <path
                d={`M ${s.median[0][0]} ${s.median[0][1]} ${s.median
                  .slice(1)
                  .map(([x, y]) => `L ${x} ${y}`)
                  .join(" ")}`}
                fill="none"
                stroke="#f97316"
                strokeWidth={48}
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            ) : null}
          </React.Fragment>
        ))}
      </g>
      <g fontFamily="monospace" fontSize={28} fill="#64748b">
        <text x={12} y={32}>
          {record.glyph_id}
        </text>
        <text x={12} y={h - 12}>
          {record.stroke_instances.length} strokes · iou{" "}
          {record.metadata?.iou_report?.mean?.toFixed(2) ?? "n/a"}/
          {record.metadata?.iou_report?.min?.toFixed(2) ?? "n/a"}
        </text>
      </g>
    </svg>
  );
};
