import * as React from "react";
import { Handle, Position, type NodeProps } from "@xyflow/react";
import { InputAdapterChip, ModeIndicator } from "@olik/glyph-viz";
import type { PlacementNodeData } from "./types.js";

export const PlacementNode: React.FC<NodeProps<{ data: PlacementNodeData }>> = ({ data }) => {
  const node = data.node;

  return (
    <div
      style={{
        border: "1px solid #a855f7",
        background: "#faf5ff",
        padding: 8,
        borderRadius: 6,
        width: 220,
        fontFamily: "system-ui, sans-serif",
      }}
    >
      <Handle type="target" position={Position.Top} />
      <div style={{ fontSize: 12, fontFamily: "monospace", fontWeight: 600 }}>{node.id}</div>
      {node.prototype_ref ? <div style={{ fontSize: 11, color: "#64748b" }}>{node.prototype_ref}</div> : null}
      {node.mode ? (
        <svg width={120} height={18}>
          <ModeIndicator mode={node.mode} />
        </svg>
      ) : null}
      {node.input_adapter ? (
        <svg width={120} height={20}>
          <InputAdapterChip adapter={node.input_adapter} />
        </svg>
      ) : null}
      <div style={{ fontSize: 10, fontFamily: "monospace", color: "#334155" }}>
        bbox: [{node.bbox.map((value) => Math.round(value)).join(", ")}]
      </div>
      <Handle type="source" position={Position.Bottom} />
    </div>
  );
};
