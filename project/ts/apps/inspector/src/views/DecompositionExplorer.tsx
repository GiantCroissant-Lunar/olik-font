import * as React from "react";
import dagre from "@dagrejs/dagre";
import { ReactFlow, type Edge, type Node } from "@xyflow/react";
import { DecompNode, NODE_TYPE_KEYS } from "@olik/flow-nodes";
import type { LayoutNode } from "@olik/glyph-schema";
import { useAppState } from "../state.js";

type ExplorerNodeTone = "leaf" | "measured" | "refine" | "replaced";

interface ExplorerNodeData extends Record<string, unknown> {
  char: string;
  operator: string | null;
  components: readonly string[];
  wouldMode?: "keep" | "refine" | "replace";
  ruleId?: string;
  sourceBadge?: string | null;
  tone: ExplorerNodeTone;
}

const nodeTypes = { [NODE_TYPE_KEYS.decomp]: DecompNode };
const NODE_WIDTH = 180;
const NODE_HEIGHT = 126;
const EDGE_COLOR = "#94a3b8";
const SOURCE_BADGES = new Set(["authored", "animcjk", "mmh", "cjk-decomp"]);

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
    <div
      data-testid="decomposition-explorer"
      style={{
        height: "calc(100vh - 160px)",
        background:
          "radial-gradient(circle at top, rgba(14,165,233,0.08), transparent 40%), #f8fafc",
      }}
    >
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        fitView
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable={false}
        minZoom={0.2}
        defaultEdgeOptions={{ style: { stroke: EDGE_COLOR, strokeWidth: 1.5 } }}
      />
    </div>
  );
};

export function layoutTreeToFlow(
  root: LayoutNode,
  rootChar: string,
): { nodes: Node<ExplorerNodeData>[]; edges: Edge[] } {
  const graph = new dagre.graphlib.Graph();
  graph.setGraph({
    rankdir: "TB",
    ranksep: 96,
    nodesep: 48,
    marginx: 40,
    marginy: 24,
  });
  graph.setDefaultEdgeLabel(() => ({}));

  const entries: Array<{ node: LayoutNode; parentId: string | null }> = [];
  const edges: Edge[] = [];

  (function visit(node: LayoutNode, parentId: string | null) {
    entries.push({ node, parentId });
    graph.setNode(node.id, { width: NODE_WIDTH, height: NODE_HEIGHT });
    if (parentId) {
      graph.setEdge(parentId, node.id);
      edges.push({
        id: `${parentId}->${node.id}`,
        source: parentId,
        target: node.id,
      });
    }
    (node.children ?? []).forEach((child) => visit(child, node.id));
  })(root, null);

  dagre.layout(graph);

  const nodes = entries.map(({ node, parentId }) => {
    const position = graph.node(node.id);
    return {
      id: node.id,
      position: {
        x: position.x - NODE_WIDTH / 2,
        y: position.y - NODE_HEIGHT / 2,
      },
      type: NODE_TYPE_KEYS.decomp,
      data: {
        char: parentId === null ? rootChar : labelForNode(node),
        operator: operatorForNode(node),
        components: (node.children ?? []).map(labelForNode),
        wouldMode: node.mode,
        ruleId: node.input_adapter,
        sourceBadge: sourceBadgeForNode(node),
        tone: toneForNode(node),
      },
    } satisfies Node<ExplorerNodeData>;
  });

  return { nodes, edges };
}

function labelForNode(node: LayoutNode): string {
  return node.prototype_ref?.replace("proto:", "") ?? node.id;
}

function operatorForNode(node: LayoutNode): string | null {
  const source = node.decomp_source as { operator?: string | null } | undefined;
  return source?.operator ?? null;
}

function sourceBadgeForNode(node: LayoutNode): string | null {
  const source = node.decomp_source as
    | { source?: string | null; adapter?: string | null }
    | undefined;
  const candidate = source?.source ?? source?.adapter ?? null;
  return candidate && SOURCE_BADGES.has(candidate) ? candidate : null;
}

function toneForNode(node: LayoutNode): ExplorerNodeTone {
  if (node.mode === "replace" || node.input_adapter === "replaced") {
    return "replaced";
  }
  if ((node.children?.length ?? 0) === 0 || node.input_adapter === "leaf") {
    return "leaf";
  }
  if (node.mode === "refine" || node.input_adapter === "refine") {
    return "refine";
  }
  return "measured";
}
