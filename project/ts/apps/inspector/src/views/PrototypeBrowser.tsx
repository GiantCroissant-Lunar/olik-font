import * as React from "react";
import {
  Background,
  Controls,
  ReactFlow,
  type Edge,
  type Node,
  type NodeProps,
} from "@xyflow/react";
import type { PrototypeBrowserData } from "@olik/glyph-loader";
import type {
  PrototypeGraphEdge,
  PrototypeGraphNode,
} from "@olik/glyph-schema";
import { useAppState } from "../state.js";

const NODE_WIDTH = 172;
const NODE_HEIGHT = 104;
const VIEW_WIDTH = 900;
const VIEW_HEIGHT = 640;
const EDGE_COLORS: Record<PrototypeGraphEdge["relation"], string> = {
  variant_of: "#7c3aed",
  decomposes_into: "#0ea5e9",
};
const PROTOTYPE_NODE_TYPE = "prototype-browser-node";

interface PrototypeNodeData extends Record<string, unknown> {
  label: string;
  caption: string;
  kind: PrototypeGraphNode["kind"];
}

const nodeTypes = {
  [PROTOTYPE_NODE_TYPE]: PrototypeBrowserNode,
};

export const PrototypeBrowser: React.FC = () => {
  const [state, dispatch] = useAppState();
  const graph = state.prototypeGraphs[state.protoId];
  const [page, setPage] = React.useState(0);

  React.useEffect(() => {
    setPage(0);
  }, [state.protoId]);

  if (!graph) {
    return <div style={{ padding: 24 }}>loading prototype graph for {state.protoId}…</div>;
  }

  const flow = buildPrototypeFlow(graph);
  const appearsIn = [...graph.appearsIn]
    .sort((left, right) => right.productive_count - left.productive_count || left.char.localeCompare(right.char))
    .slice(0, 50);
  const pageSize = 10;
  const pageCount = Math.max(1, Math.ceil(appearsIn.length / pageSize));
  const clampedPage = Math.min(page, pageCount - 1);
  const visible = appearsIn.slice(clampedPage * pageSize, clampedPage * pageSize + pageSize);

  return (
    <div
      data-testid="prototype-browser"
      style={{
        height: "calc(100vh - 112px)",
        display: "grid",
        gridTemplateColumns: "minmax(0, 1fr) 320px",
        gap: 16,
        padding: 16,
        background:
          "radial-gradient(circle at top, rgba(124,58,237,0.08), transparent 35%), #f8fafc",
      }}
    >
      <section
        style={{
          minWidth: 0,
          border: "1px solid #d8dee8",
          borderRadius: 16,
          background: "#ffffff",
          overflow: "hidden",
          boxShadow: "0 18px 40px rgba(15, 23, 42, 0.08)",
        }}
      >
        <header
          style={{
            padding: "16px 18px 12px",
            borderBottom: "1px solid #e2e8f0",
            display: "flex",
            justifyContent: "space-between",
            gap: 12,
            alignItems: "center",
          }}
        >
          <div>
            <div style={{ fontSize: 12, letterSpacing: "0.08em", textTransform: "uppercase", color: "#64748b" }}>
              Prototype Browser
            </div>
            <div style={{ display: "flex", alignItems: "baseline", gap: 10 }}>
              <div style={{ fontSize: 34, fontFamily: "serif", color: "#0f172a" }}>{graph.focus.label}</div>
              <div style={{ fontSize: 12, fontFamily: "monospace", color: "#64748b" }}>
                {graph.focus.id}
              </div>
            </div>
          </div>
          <button
            onClick={() => dispatch({ type: "setProtoId", protoId: state.protoId })}
            style={{
              border: "1px solid #cbd5e1",
              background: "#f8fafc",
              color: "#0f172a",
              borderRadius: 999,
              padding: "8px 12px",
              cursor: "pointer",
            }}
          >
            /proto/{state.protoId}
          </button>
        </header>
        <div
          style={{
            display: "flex",
            gap: 8,
            flexWrap: "wrap",
            padding: "12px 18px 0",
          }}
        >
          <MetaChip label="role" value={graph.focus.role} />
          <MetaChip label="etymology" value={graph.focus.etymology ?? "n/a"} />
          <MetaChip label="productive_count" value={String(graph.focus.productive_count)} />
        </div>
        <div style={{ height: "calc(100% - 124px)" }}>
          <ReactFlow
            nodes={flow.nodes}
            edges={flow.edges}
            nodeTypes={nodeTypes}
            fitView
            nodesDraggable={false}
            nodesConnectable={false}
            panOnScroll
            minZoom={0.45}
            fitViewOptions={{ padding: 0.16 }}
          >
            <Background color="#e2e8f0" gap={24} />
            <Controls showInteractive={false} />
          </ReactFlow>
        </div>
      </section>
      <aside
        style={{
          border: "1px solid #d8dee8",
          borderRadius: 16,
          background: "#ffffff",
          padding: 16,
          display: "flex",
          flexDirection: "column",
          gap: 14,
          boxShadow: "0 18px 40px rgba(15, 23, 42, 0.08)",
        }}
      >
        <div>
          <div style={{ fontSize: 12, letterSpacing: "0.08em", textTransform: "uppercase", color: "#64748b" }}>
            appears_in
          </div>
          <div style={{ fontSize: 22, color: "#0f172a", marginTop: 4 }}>
            Glyph reuse
          </div>
          <div style={{ fontSize: 13, color: "#475569", marginTop: 6 }}>
            Top {appearsIn.length} glyphs sorted by productive_count descending.
          </div>
        </div>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
            gap: 10,
          }}
        >
          {visible.map((item) => (
            <div
              key={item.char}
              style={{
                border: "1px solid #d8dee8",
                borderRadius: 12,
                padding: "12px 10px",
                background: "#f8fafc",
              }}
            >
              <div style={{ fontSize: 28, fontFamily: "serif", color: "#0f172a" }}>{item.char}</div>
              <div style={{ fontSize: 11, color: "#64748b", marginTop: 4 }}>
                productive_count
              </div>
              <div style={{ fontSize: 16, color: "#0f172a" }}>{item.productive_count}</div>
            </div>
          ))}
        </div>
        <div
          style={{
            marginTop: "auto",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <button
            onClick={() => setPage((current) => Math.max(0, current - 1))}
            disabled={clampedPage === 0}
            style={pagerButtonStyle(clampedPage === 0)}
          >
            Prev
          </button>
          <div style={{ fontSize: 12, color: "#475569" }}>
            page {clampedPage + 1} / {pageCount}
          </div>
          <button
            onClick={() => setPage((current) => Math.min(pageCount - 1, current + 1))}
            disabled={clampedPage >= pageCount - 1}
            style={pagerButtonStyle(clampedPage >= pageCount - 1)}
          >
            Next
          </button>
        </div>
      </aside>
    </div>
  );
};

export function buildPrototypeFlow(graph: PrototypeBrowserData): {
  nodes: Node<PrototypeNodeData>[];
  edges: Edge[];
} {
  const positions = layoutPrototypeGraph(graph.nodes, graph.edges);
  return {
    nodes: graph.nodes.map((node: PrototypeGraphNode) => ({
      id: node.id,
      type: PROTOTYPE_NODE_TYPE,
      position: positions.get(node.id) ?? { x: 0, y: 0 },
      data: {
        label: node.label,
        caption: node.id,
        kind: node.kind,
      },
    })),
    edges: graph.edges.map((edge: PrototypeGraphEdge) => ({
      id: edge.id,
      source: edge.source,
      target: edge.target,
      label: edge.relation === "variant_of" ? "variant_of" : "decomposes_into",
      labelStyle: { fill: EDGE_COLORS[edge.relation], fontSize: 11, fontWeight: 600 },
      style: { stroke: EDGE_COLORS[edge.relation], strokeWidth: 1.8 },
      type: "smoothstep",
      animated: edge.relation === "variant_of",
    })),
  };
}

function layoutPrototypeGraph(
  nodes: PrototypeGraphNode[],
  edges: PrototypeGraphEdge[],
): Map<string, { x: number; y: number }> {
  const center = { x: VIEW_WIDTH / 2, y: VIEW_HEIGHT / 2 - 18 };
  const positions = new Map<string, { x: number; y: number }>();
  const degrees = new Map<string, number>();
  const childNodes = nodes.filter((node) => node.kind === "child");
  const parentNodes = nodes.filter((node) => node.kind === "variant-parent");
  const siblingNodes = nodes.filter((node) => node.kind === "variant-sibling");

  for (const node of nodes) {
    degrees.set(node.id, 0);
    positions.set(
      node.id,
      initialPositionForNode(node, center, {
        childIndex: childNodes.findIndex((candidate) => candidate.id === node.id),
        childCount: childNodes.length,
        parentIndex: parentNodes.findIndex((candidate) => candidate.id === node.id),
        siblingIndex: siblingNodes.findIndex((candidate) => candidate.id === node.id),
      }),
    );
  }
  for (const edge of edges) {
    degrees.set(edge.source, (degrees.get(edge.source) ?? 0) + 1);
    degrees.set(edge.target, (degrees.get(edge.target) ?? 0) + 1);
  }

  const focus = nodes.find((node) => node.kind === "focus");
  if (!focus) {
    return positions;
  }
  positions.set(focus.id, center);

  for (let step = 0; step < 140; step += 1) {
    for (const node of nodes) {
      if (node.id === focus.id) {
        positions.set(node.id, center);
        continue;
      }
      const current = positions.get(node.id)!;
      let dx = 0;
      let dy = 0;

      for (const peer of nodes) {
        if (peer.id === node.id) continue;
        const other = positions.get(peer.id)!;
        const diffX = current.x - other.x;
        const diffY = current.y - other.y;
        const distanceSq = Math.max(diffX * diffX + diffY * diffY, 1);
        const repulsion = 26000 / distanceSq;
        dx += (diffX / Math.sqrt(distanceSq)) * repulsion;
        dy += (diffY / Math.sqrt(distanceSq)) * repulsion;
      }

      for (const edge of edges) {
        const source = positions.get(edge.source)!;
        const target = positions.get(edge.target)!;
        if (edge.source !== node.id && edge.target !== node.id) {
          continue;
        }
        const sign = edge.source === node.id ? 1 : -1;
        const diffX = target.x - source.x;
        const diffY = target.y - source.y;
        const distance = Math.max(Math.hypot(diffX, diffY), 1);
        const desired = edge.relation === "variant_of" ? 200 : 220;
        const spring = (distance - desired) * 0.04;
        dx += sign * (diffX / distance) * spring;
        dy += sign * (diffY / distance) * spring;
      }

      const degree = degrees.get(node.id) ?? 1;
      dx += (center.x - current.x) * 0.008 * degree;
      dy += verticalBias(node.kind, center.y - current.y);

      positions.set(node.id, {
        x: clamp(current.x + dx, 24, VIEW_WIDTH - NODE_WIDTH - 24),
        y: clamp(current.y + dy, 24, VIEW_HEIGHT - NODE_HEIGHT - 24),
      });
    }
  }

  return positions;
}

function initialPositionForNode(
  node: PrototypeGraphNode,
  center: { x: number; y: number },
  indexes: {
    childIndex: number;
    childCount: number;
    parentIndex: number;
    siblingIndex: number;
  },
): { x: number; y: number } {
  switch (node.kind) {
    case "focus":
      return { x: center.x, y: center.y };
    case "variant-parent":
      return { x: center.x - 210 + indexes.parentIndex * 90, y: center.y - 178 };
    case "variant-sibling":
      return { x: center.x + 120 + indexes.siblingIndex * 90, y: center.y - 152 };
    case "child":
      return {
        x: center.x + (indexes.childIndex - (indexes.childCount - 1) / 2) * 168,
        y: center.y + 208,
      };
  }
  return assertNever(node.kind);
}

function verticalBias(kind: PrototypeGraphNode["kind"], deltaToCenter: number): number {
  switch (kind) {
    case "variant-parent":
      return (deltaToCenter - 170) * 0.015;
    case "variant-sibling":
      return (deltaToCenter - 150) * 0.015;
    case "child":
      return (deltaToCenter + 180) * 0.018;
    case "focus":
      return 0;
  }
  return assertNever(kind);
}

function PrototypeBrowserNode({ data }: NodeProps<Node<PrototypeNodeData>>): React.ReactElement {
  return (
    <div
      style={{
        width: NODE_WIDTH,
        minHeight: NODE_HEIGHT,
        borderRadius: 18,
        border: `1px solid ${borderForKind(data.kind)}`,
        background: backgroundForKind(data.kind),
        boxShadow: "0 10px 30px rgba(15, 23, 42, 0.10)",
        padding: "14px 16px",
      }}
    >
      <div
        style={{
          display: "inline-flex",
          borderRadius: 999,
          background: "#ffffffcc",
          border: "1px solid #d8dee8",
          padding: "3px 8px",
          fontSize: 10,
          letterSpacing: "0.06em",
          textTransform: "uppercase",
          color: "#475569",
        }}
      >
        {data.kind.replace("-", " ")}
      </div>
      <div style={{ fontSize: 30, fontFamily: "serif", color: "#0f172a", marginTop: 10 }}>
        {data.label}
      </div>
      <div style={{ fontSize: 11, fontFamily: "monospace", color: "#475569", marginTop: 6 }}>
        {data.caption}
      </div>
    </div>
  );
}

const MetaChip: React.FC<{ label: string; value: string }> = ({ label, value }) => (
  <div
    style={{
      border: "1px solid #d8dee8",
      background: "#f8fafc",
      borderRadius: 999,
      padding: "8px 12px",
    }}
  >
    <span style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: "0.06em", color: "#64748b" }}>
      {label}
    </span>
    <span style={{ marginLeft: 8, fontSize: 14, color: "#0f172a" }}>{value}</span>
  </div>
);

function borderForKind(kind: PrototypeGraphNode["kind"]): string {
  switch (kind) {
    case "focus":
      return "#0f172a";
    case "variant-parent":
      return "#7c3aed";
    case "variant-sibling":
      return "#a855f7";
    case "child":
      return "#0ea5e9";
  }
  return assertNever(kind);
}

function backgroundForKind(kind: PrototypeGraphNode["kind"]): string {
  switch (kind) {
    case "focus":
      return "linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%)";
    case "variant-parent":
      return "linear-gradient(135deg, #f5f3ff 0%, #ede9fe 100%)";
    case "variant-sibling":
      return "linear-gradient(135deg, #faf5ff 0%, #f3e8ff 100%)";
    case "child":
      return "linear-gradient(135deg, #ecfeff 0%, #e0f2fe 100%)";
  }
  return assertNever(kind);
}

function pagerButtonStyle(disabled: boolean): React.CSSProperties {
  return {
    border: "1px solid #cbd5e1",
    background: disabled ? "#e2e8f0" : "#f8fafc",
    color: disabled ? "#94a3b8" : "#0f172a",
    borderRadius: 999,
    padding: "8px 12px",
    cursor: disabled ? "default" : "pointer",
  };
}

function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value));
}

function assertNever(value: never): never {
  throw new Error(`unexpected value: ${String(value)}`);
}
