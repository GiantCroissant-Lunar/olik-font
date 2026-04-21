import * as React from "react";
import { AbsoluteFill } from "remotion";
import {
  AnchorBindingArrow, AnchorMarker, BBoxOverlay, StrokePath, VirtualCoordGrid,
} from "@olik/glyph-viz";
import type { GlyphBundle } from "@olik/glyph-loader";

export interface VirtualCoordProps extends Record<string, unknown> {
  bundle: GlyphBundle;
  char: string;
}

export const VirtualCoord: React.FC<VirtualCoordProps> = ({ bundle, char }) => {
  const record = bundle.records[char];
  if (!record) return null;

  const glyphSize = 640;
  void AnchorBindingArrow;
  void AnchorMarker;
  return (
    <AbsoluteFill style={{ background: "#ffffff" }}>
      <svg width={1280} height={720}>
        <g transform={`translate(${(1280 - glyphSize) / 2}, 40) scale(${glyphSize / 1024})`}>
          <VirtualCoordGrid />
          {record.stroke_instances.map((s) => (
            <StrokePath
              key={s.id}
              outlinePath={s.path}
              median={s.median as Array<[number, number]>}
              progress={1}
            />
          ))}
          {record.component_instances.map((inst) => (
            inst.placed_bbox ? (
              <BBoxOverlay
                key={inst.id}
                bbox={inst.placed_bbox}
                label={inst.id}
                color="#0ea5e9"
                dashed
              />
            ) : null
          ))}
          {record.layout_tree.anchor_bindings?.map((ab, i) => {
            // best-effort: resolve anchor endpoints where possible, else skip
            // pass 1 layout-tree typically has none at root
            void ab;
            void i;
            return null;
          })}
        </g>
      </svg>
    </AbsoluteFill>
  );
};
