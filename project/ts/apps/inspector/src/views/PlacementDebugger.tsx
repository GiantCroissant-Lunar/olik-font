import * as React from "react";
import { ReactFlow, type Edge, type Node } from "@xyflow/react";
import { NODE_TYPE_KEYS, PlacementNode } from "@olik/flow-nodes";
import type { LayoutNode } from "@olik/glyph-schema";
import { useAppState } from "../state.js";

const nodeTypes = { [NODE_TYPE_KEYS.placement]: PlacementNode };

export const PlacementDebugger: React.FC = () => {
  const [state] = useAppState();
  const record = state.records[state.char];

  if (!record) {
    return <div style={{ padding: 24 }}>no record for {state.char}</div>;
  }

  const { nodes, edges } = toFlow(record.layout_tree);

  return (
    <div style={{ height: "calc(100vh - 160px)" }}>
      <ReactFlow nodes={nodes} edges={edges} nodeTypes={nodeTypes} fitView />
    </div>
  );
};

function toFlow(root: LayoutNode): { nodes: Node[]; edges: Edge[] } {
  const nodes: Node[] = [];
  const edges: Edge[] = [];

  const levels = new Map<number, LayoutNode[]>();
  (function index(node: LayoutNode, depth: number) {
    const arr = levels.get(depth) ?? [];
    arr.push(node);
    levels.set(depth, arr);
    (node.children ?? []).forEach((child) => index(child, depth + 1));
  })(root, 0);

  const dx = 260;
  const dy = 180;
  const positions = new Map<string, { x: number; y: number }>();

  for (const [depth, arr] of levels.entries()) {
    const start = -((arr.length - 1) * dx) / 2;
    arr.forEach((node, i) => {
      positions.set(node.id, { x: 640 + start + i * dx, y: 60 + depth * dy });
    });
  }

  (function build(node: LayoutNode, parentId: string | null) {
    nodes.push({
      id: node.id,
      position: positions.get(node.id)!,
      type: NODE_TYPE_KEYS.placement,
      data: { node },
    });

    if (parentId) {
      edges.push({ id: `${parentId}->${node.id}`, source: parentId, target: node.id });
    }

    (node.children ?? []).forEach((child) => build(child, node.id));
  })(root, null);

  return { nodes, edges };
}
