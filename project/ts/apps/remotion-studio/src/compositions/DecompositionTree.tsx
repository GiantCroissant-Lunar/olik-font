import * as React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import {
  InputAdapterChip, ModeIndicator, TreeLayout,
} from "@olik/glyph-viz";
import type { GlyphBundle } from "@olik/glyph-loader";
import type { LayoutNode } from "@olik/glyph-schema";
import { strokeProgress } from "../timing.js";

export interface DecompositionTreeProps extends Record<string, unknown> {
  bundle: GlyphBundle;
  char: string;
  framesPerStroke: number;
}

export const DecompositionTree: React.FC<DecompositionTreeProps> = ({
  bundle, char, framesPerStroke,
}) => {
  const frame = useCurrentFrame();
  const record = bundle.records[char];
  if (!record) return null;

  const lit = litNodes(record.layout_tree, record.stroke_instances, frame, framesPerStroke);

  return (
    <AbsoluteFill style={{ background: "#ffffff" }}>
      <svg width={1280} height={720}>
        <g transform="translate(40, 40)">
          <TreeLayout
            root={record.layout_tree}
            width={1200}
            height={640}
            renderNode={(n: LayoutNode) => (
              <g>
                <circle
                  r={10}
                  fill={lit.has(n.id) ? "#10b981" : "#cbd5e1"}
                  stroke="#475569"
                  strokeWidth={1}
                />
                <text x={14} y={4} fontSize={13} fontFamily="monospace">
                  {n.prototype_ref ?? n.id}
                </text>
                {n.mode ? <ModeIndicator mode={n.mode} x={14} y={14} /> : null}
                {n.input_adapter ? <InputAdapterChip adapter={n.input_adapter} x={14} y={34} /> : null}
              </g>
            )}
          />
        </g>
      </svg>
    </AbsoluteFill>
  );
};

function litNodes(
  root: LayoutNode,
  strokes: ReadonlyArray<{ instance_id: string }>,
  frame: number,
  framesPerStroke: number,
): Set<string> {
  const drawn = new Set<string>();
  strokes.forEach((s, i) => {
    if (strokeProgress({ frame, strokeIndex: i, framesPerStroke }) >= 1) {
      drawn.add(s.instance_id);
    }
  });

  const lit = new Set<string>();
  function dfs(n: LayoutNode): boolean {
    const kids = n.children ?? [];
    if (kids.length === 0) {
      if (drawn.has(n.id)) {
        lit.add(n.id);
        return true;
      }
      return false;
    }
    const allDrawn = kids.every(dfs);
    if (allDrawn) lit.add(n.id);
    return allDrawn;
  }
  dfs(root);
  return lit;
}
