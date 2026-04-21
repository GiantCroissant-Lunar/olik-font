import * as React from "react";
import { AbsoluteFill } from "remotion";
import { LayerStack } from "@olik/glyph-viz";
import type { GlyphBundle } from "@olik/glyph-loader";

export interface LayerZDepthProps extends Record<string, unknown> {
  bundle: GlyphBundle;
  char: string;
}

export const LayerZDepth: React.FC<LayerZDepthProps> = ({ bundle, char }) => {
  const record = bundle.records[char];
  if (!record) return null;
  return (
    <AbsoluteFill style={{ background: "#ffffff" }}>
      <svg width={1280} height={720}>
        <g transform="translate(40, 40)">
          <LayerStack
            layers={record.render_layers}
            strokes={record.stroke_instances}
            panelHeight={120}
            panelWidth={180}
          />
        </g>
        <g transform="translate(260, 40)">
          <text fontSize={32} fontFamily="serif">{char}</text>
          <text y={30} fontSize={13} fontFamily="monospace" fill="#64748b">
            render_layers × stroke_instances
          </text>
        </g>
      </svg>
    </AbsoluteFill>
  );
};
