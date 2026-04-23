import * as React from "react";
import { Handle, Position, type Node, type NodeProps } from "@xyflow/react";
import { NODE_TYPE_KEYS, type DecompNodeData } from "./types.js";

type DecompFlowNode = Node<DecompNodeData, typeof NODE_TYPE_KEYS.decomp>;

const TONE_STYLES = {
  leaf: { border: "#64748b", background: "#f8fafc", chip: "#475569" },
  measured: { border: "#0ea5e9", background: "#f0f9ff", chip: "#0369a1" },
  refine: { border: "#d97706", background: "#fffbeb", chip: "#b45309" },
  replaced: { border: "#a855f7", background: "#faf5ff", chip: "#7e22ce" },
} as const;

export const DecompNode: React.FC<NodeProps<DecompFlowNode>> = ({ data, selected }) => {
  const tone = data.tone ?? "measured";
  const style = TONE_STYLES[tone];

  return (
    <div
      data-testid="decomp-node"
      style={{
        border: `2px solid ${style.border}`,
        background: style.background,
        padding: 10,
        borderRadius: 10,
        width: 180,
        fontFamily: "system-ui, sans-serif",
        boxShadow: selected
          ? "0 0 0 3px rgba(15, 23, 42, 0.12), 0 16px 32px rgba(15, 23, 42, 0.16)"
          : "0 10px 24px rgba(15, 23, 42, 0.08)",
      }}
    >
      <Handle type="target" position={Position.Top} />
      <div style={{ fontSize: 30, fontFamily: "serif", textAlign: "center" }}>{data.char}</div>
      <div style={{ fontSize: 11, color: "#64748b", textAlign: "center" }}>
        op: {data.operator ?? "atomic"}
      </div>
      {data.components.length > 0 ? (
        <div style={{ fontSize: 11, marginTop: 6, color: "#0f172a" }}>
          → {data.components.join(", ")}
        </div>
      ) : null}
      <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginTop: 8 }}>
        {data.wouldMode ? (
          <span
            style={{
              fontSize: 11,
              lineHeight: 1,
              padding: "4px 8px",
              borderRadius: 999,
              border: `1px solid ${style.chip}`,
              color: style.chip,
              background: "#ffffff",
              fontFamily: "monospace",
            }}
          >
            {data.wouldMode}
          </span>
        ) : null}
        {data.sourceBadge ? (
          <span
            style={{
              fontSize: 11,
              lineHeight: 1,
              padding: "4px 8px",
              borderRadius: 999,
              border: "1px solid #cbd5e1",
              color: "#334155",
              background: "#ffffff",
              fontFamily: "monospace",
            }}
          >
            {data.sourceBadge}
          </span>
        ) : null}
      </div>
      {data.ruleId ? (
        <div
          style={{
            fontSize: 10,
            color: "#475569",
            fontFamily: "monospace",
            marginTop: 8,
            wordBreak: "break-word",
          }}
        >
          {data.ruleId}
        </div>
      ) : null}
      <Handle type="source" position={Position.Bottom} />
    </div>
  );
};
