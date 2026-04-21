import * as React from "react";
import { Handle, Position, type Node, type NodeProps } from "@xyflow/react";
import { StrokePath } from "@olik/glyph-viz";
import { NODE_TYPE_KEYS, type PrototypeNodeData } from "./types.js";

type PrototypeFlowNode = Node<PrototypeNodeData, typeof NODE_TYPE_KEYS.prototype>;

export const PrototypeNode: React.FC<NodeProps<PrototypeFlowNode>> = ({ data }) => {
  const { prototype, instanceCount, hostingChars } = data;

  return (
    <div
      style={{
        border: "1px solid #475569",
        background: "#ffffff",
        padding: 8,
        borderRadius: 6,
        width: 180,
        fontFamily: "system-ui, sans-serif",
      }}
    >
      <Handle type="target" position={Position.Left} />
      <div style={{ fontSize: 22, fontFamily: "serif" }}>{prototype.name}</div>
      <div style={{ fontSize: 10, color: "#64748b", fontFamily: "monospace" }}>{prototype.id}</div>
      <svg width={120} height={120} viewBox="0 0 1024 1024" style={{ display: "block", margin: "8px 0" }}>
        {/* MMH strokes are y-up; flip to SVG y-down so the char reads right-side up. */}
        <g transform="translate(0,1024) scale(1,-1)">
          {prototype.strokes.map((stroke) => (
            <StrokePath
              key={stroke.id}
              outlinePath={stroke.path}
              median={stroke.median as Array<[number, number]>}
              progress={1}
              strokeWidth={48}
            />
          ))}
        </g>
      </svg>
      <div style={{ fontSize: 11 }}>
        <div>uses: {instanceCount}</div>
        <div>chars: {hostingChars.join(" ")}</div>
      </div>
      <Handle type="source" position={Position.Right} />
    </div>
  );
};
