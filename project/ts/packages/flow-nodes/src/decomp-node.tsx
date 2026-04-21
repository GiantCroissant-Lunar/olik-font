import * as React from "react";
import { Handle, Position, type Node, type NodeProps } from "@xyflow/react";
import { ModeIndicator } from "@olik/glyph-viz";
import { NODE_TYPE_KEYS, type DecompNodeData } from "./types.js";

type DecompFlowNode = Node<DecompNodeData, typeof NODE_TYPE_KEYS.decomp>;

export const DecompNode: React.FC<NodeProps<DecompFlowNode>> = ({ data }) => {
  return (
    <div
      style={{
        border: "1px solid #0ea5e9",
        background: "#f0f9ff",
        padding: 8,
        borderRadius: 6,
        width: 140,
        fontFamily: "system-ui, sans-serif",
      }}
    >
      <Handle type="target" position={Position.Top} />
      <div style={{ fontSize: 28, fontFamily: "serif", textAlign: "center" }}>{data.char}</div>
      <div style={{ fontSize: 11, color: "#64748b" }}>op: {data.operator ?? "atomic"}</div>
      {data.components.length > 0 ? <div style={{ fontSize: 11 }}>→ {data.components.join(", ")}</div> : null}
      {data.wouldMode ? (
        <svg width={100} height={18}>
          <ModeIndicator mode={data.wouldMode} />
        </svg>
      ) : null}
      {data.ruleId ? (
        <div style={{ fontSize: 10, color: "#0ea5e9", fontFamily: "monospace" }}>{data.ruleId}</div>
      ) : null}
      <Handle type="source" position={Position.Bottom} />
    </div>
  );
};
