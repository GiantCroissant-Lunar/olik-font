import * as React from "react";
import { ReactFlow, type Edge, type Node } from "@xyflow/react";
import { DecompNode, NODE_TYPE_KEYS } from "@olik/flow-nodes";
import type { LayoutNode } from "@olik/glyph-schema";
import { useAppState } from "../state.js";

const nodeTypes = { [NODE_TYPE_KEYS.decomp]: DecompNode };

export const DecompositionExplorer: React.FC = () => {
  const [state] = useAppState();
  const record = state.records[state.char];

  if (!record) {
    return <div style={{ padding: 24 }}>no record for {state.char}</div>;
  }

  if (!record.layout_tree) {
    return <div style={{ padding: 24 }}>no layout tree for {state.char}</div>;
  }

  const { nodes, edges } = layoutTreeToFlow(record.layout_tree, record.glyph_id);

  return (
    <div style={{ height: "calc(100vh - 160px)" }}>
      <ReactFlow nodes={nodes} edges={edges} nodeTypes={nodeTypes} fitView />
    </div>
  );
};

function layoutTreeToFlow(root: LayoutNode, rootChar: string): { nodes: Node[]; edges: Edge[] } {
  const nodes: Node[] = [];
  const edges: Edge[] = [];

  const levels = new Map<number, LayoutNode[]>();
  (function index(node: LayoutNode, depth: number) {
    const arr = levels.get(depth) ?? [];
    arr.push(node);
    levels.set(depth, arr);
    (node.children ?? []).forEach((child) => index(child, depth + 1));
  })(root, 0);

  const dx = 220;
  const dy = 140;
  const positions = new Map<string, { x: number; y: number }>();

  for (const [depth, arr] of levels.entries()) {
    const start = -((arr.length - 1) * dx) / 2;
    arr.forEach((node, i) => {
      positions.set(node.id, { x: 640 + start + i * dx, y: 60 + depth * dy });
    });
  }

  (function build(node: LayoutNode, parentId: string | null) {
    const pos = positions.get(node.id)!;
    const isRoot = parentId === null;
    const label = isRoot ? rootChar : node.prototype_ref?.replace("proto:", "") ?? node.id;

    nodes.push({
      id: node.id,
      position: pos,
      type: NODE_TYPE_KEYS.decomp,
      data: {
        char: label,
        operator: (node.decomp_source as { operator?: string } | undefined)?.operator ?? null,
        components: (node.children ?? []).map((child) => child.prototype_ref?.replace("proto:", "") ?? child.id),
        wouldMode: node.mode,
        ruleId: node.input_adapter,
      },
    });

    if (parentId) {
      edges.push({ id: `${parentId}->${node.id}`, source: parentId, target: node.id });
    }

    (node.children ?? []).forEach((child) => build(child, node.id));
  })(root, null);

  return { nodes, edges };
}
