import * as React from "react";
import { Handle, Position, type NodeProps } from "@xyflow/react";
import type { RuleNodeData } from "./types.js";

const BUCKET_COLOR: Record<RuleNodeData["bucket"], string> = {
  decomposition: "#0ea5e9",
  composition: "#a855f7",
  prototype_extraction: "#d97706",
};

export const RuleNode: React.FC<
  NodeProps<{ data: RuleNodeData & { firedInView?: boolean; isAlternativeInView?: boolean } }>
> = ({ data }) => {
  const color = BUCKET_COLOR[data.bucket];
  const bg = data.firedInView ? "#dcfce7" : data.isAlternativeInView ? "#fef3c7" : "#ffffff";
  const border = data.firedInView ? "#16a34a" : data.isAlternativeInView ? "#ca8a04" : color;

  return (
    <div
      style={{
        border: `2px solid ${border}`,
        background: bg,
        padding: 8,
        borderRadius: 6,
        width: 260,
        fontFamily: "system-ui, sans-serif",
      }}
    >
      <Handle type="target" position={Position.Top} />
      <div style={{ fontSize: 11, color, fontFamily: "monospace" }}>{data.bucket}</div>
      <div style={{ fontSize: 13, fontFamily: "monospace", fontWeight: 600 }}>{data.ruleId}</div>
      <div style={{ fontSize: 10, color: "#64748b", fontFamily: "monospace", marginTop: 4 }}>
        when: {JSON.stringify(data.when)}
      </div>
      <div style={{ fontSize: 10, color: "#64748b", fontFamily: "monospace" }}>
        → {JSON.stringify(data.action)}
      </div>
      {data.firedBy && data.firedBy.length > 0 ? (
        <div style={{ fontSize: 10, color: "#16a34a", marginTop: 4 }}>
          fired by: {data.firedBy.join(", ")}
        </div>
      ) : null}
      <Handle type="source" position={Position.Bottom} />
    </div>
  );
};
