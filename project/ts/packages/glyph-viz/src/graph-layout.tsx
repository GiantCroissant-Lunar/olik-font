import * as React from "react";

export interface GraphNode {
  id: string;
  x: number;
  y: number;
  data?: unknown;
}

export interface GraphLink {
  source: string;
  target: string;
  kind?: string;
}

export interface GraphLayoutProps {
  nodes: ReadonlyArray<GraphNode>;
  links: ReadonlyArray<GraphLink>;
  linkColor?: string;
  renderNode: (node: GraphNode) => React.ReactNode;
}

export function GraphLayout({
  nodes,
  links,
  linkColor = "#94a3b8",
  renderNode,
}: GraphLayoutProps): React.ReactElement {
  const byId = new Map(nodes.map((n) => [n.id, n] as const));

  return (
    <g className="olik-graph">
      {links.map((l, i) => {
        const s = byId.get(l.source);
        const t = byId.get(l.target);
        if (!s || !t) return null;
        return (
          <line
            key={`l${i}`}
            className="olik-graph-link"
            x1={s.x}
            y1={s.y}
            x2={t.x}
            y2={t.y}
            stroke={linkColor}
            strokeWidth={1.5}
          />
        );
      })}
      {nodes.map((n) => (
        <g key={n.id} className="olik-graph-node" transform={`translate(${n.x}, ${n.y})`}>
          {renderNode(n)}
        </g>
      ))}
    </g>
  );
}
