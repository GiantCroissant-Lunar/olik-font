import * as React from "react";
import {
  ReactFlow,
  ReactFlowProvider,
  Background,
  Controls,
  MarkerType,
  Position,
  type Edge,
  type Node,
} from "@xyflow/react";
import type { LayoutNode } from "./types.js";

// Render a glyph-record's layout_tree as an xyflow DAG. Tidy-tree-ish layout
// computed by BFS-by-depth. Each node card shows the id, prototype_ref,
// mode, and depth; refine-mode nodes get a dashed border.

function flattenByDepth(root: LayoutNode): Map<number, LayoutNode[]> {
  const byDepth = new Map<number, LayoutNode[]>();
  const visit = (node: LayoutNode, depth: number) => {
    const arr = byDepth.get(depth) ?? [];
    arr.push(node);
    byDepth.set(depth, arr);
    (node.children ?? []).forEach((c) => visit(c, depth + 1));
  };
  visit(root, 0);
  return byDepth;
}

function buildFlow(root: LayoutNode): { nodes: Node[]; edges: Edge[] } {
  const byDepth = flattenByDepth(root);
  const dx = 220;
  const dy = 140;

  const positions = new Map<string, { x: number; y: number }>();
  for (const [depth, arr] of byDepth.entries()) {
    const start = -((arr.length - 1) * dx) / 2;
    arr.forEach((n, i) => positions.set(n.id, { x: 320 + start + i * dx, y: 60 + depth * dy }));
  }

  const nodes: Node[] = [];
  const edges: Edge[] = [];

  const visit = (n: LayoutNode, parentId: string | null) => {
    const pos = positions.get(n.id)!;
    const isRefine = n.mode === "refine";
    const labelTop = n.prototype_ref?.replace("proto:", "") ?? n.id;
    nodes.push({
      id: n.id,
      position: pos,
      data: {
        label: (
          <div
            style={{
              padding: 8,
              border: isRefine ? "2px dashed #a855f7" : "1px solid #475569",
              background: "#ffffff",
              borderRadius: 6,
              minWidth: 160,
              fontFamily: "system-ui",
            }}
          >
            <div style={{ fontSize: 18, fontFamily: "serif" }}>{labelTop}</div>
            <div style={{ fontSize: 10, color: "#64748b", fontFamily: "monospace" }}>{n.id}</div>
            {n.mode ? (
              <div style={{ fontSize: 11, color: "#0f172a", marginTop: 4 }}>
                mode: <code>{n.mode}</code> · depth {n.depth ?? 0}
              </div>
            ) : null}
            {n.input_adapter ? (
              <div style={{ fontSize: 10, color: "#a855f7", fontFamily: "monospace" }}>
                {n.input_adapter}
              </div>
            ) : null}
          </div>
        ),
      },
      type: "default",
      sourcePosition: Position.Bottom,
      targetPosition: Position.Top,
    });

    if (parentId) {
      edges.push({
        id: `${parentId}->${n.id}`,
        source: parentId,
        target: n.id,
        markerEnd: { type: MarkerType.ArrowClosed },
      });
    }

    (n.children ?? []).forEach((c) => visit(c, n.id));
  };

  visit(root, null);
  return { nodes, edges };
}

interface Props {
  root: LayoutNode;
}

export const DecompTree: React.FC<Props> = ({ root }) => {
  const { nodes, edges } = React.useMemo(() => buildFlow(root), [root]);
  return (
    <div style={{ height: "100%", width: "100%", background: "#fafafa" }}>
      <ReactFlowProvider>
        <ReactFlow nodes={nodes} edges={edges} fitView attributionPosition="bottom-right">
          <Background />
          <Controls />
        </ReactFlow>
      </ReactFlowProvider>
    </div>
  );
};
