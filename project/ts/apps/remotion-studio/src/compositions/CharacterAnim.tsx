import * as React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import { IoUBadge, StrokePath, VirtualCoordGrid } from "@olik/glyph-viz";
import type { GlyphBundle } from "@olik/glyph-loader";
import { strokeProgress } from "../timing.js";

export interface CharacterAnimProps extends Record<string, unknown> {
  bundle: GlyphBundle;
  char: string;
  framesPerStroke: number;
  showGrid?: boolean;
}

export const CharacterAnim: React.FC<CharacterAnimProps> = ({
  bundle, char, framesPerStroke, showGrid = false,
}) => {
  const frame = useCurrentFrame();
  const { width, height } = useVideoConfig();
  const record = bundle.records[char];
  if (!record) return null;

  const glyphSize = 800;
  const gx = (width - glyphSize) / 2;
  const gy = (height - glyphSize) / 2;
  const iou = record.metadata?.iou_report?.mean ?? 1;

  return (
    <AbsoluteFill style={{ background: "#ffffff" }}>
      <svg width={width} height={height}>
        <g transform={`translate(${gx}, ${gy}) scale(${glyphSize / 1024})`}>
          {/* MMH strokes are y-up; flip to SVG y-down so the char reads right-side up. */}
          <g transform="translate(0,1024) scale(1,-1)">
            {showGrid ? <VirtualCoordGrid /> : null}
            {record.stroke_instances.map((s, i) => (
              <StrokePath
                key={s.id}
                outlinePath={s.path}
                median={s.median as Array<[number, number]>}
                progress={strokeProgress({ frame, strokeIndex: i, framesPerStroke })}
              />
            ))}
          </g>
        </g>
        <g transform="translate(40, 40)">
          <text fontSize={56} fontFamily="serif">{char}</text>
        </g>
        <g transform={`translate(${width - 120}, ${height - 40})`}>
          <IoUBadge value={iou} />
        </g>
      </svg>
    </AbsoluteFill>
  );
};
