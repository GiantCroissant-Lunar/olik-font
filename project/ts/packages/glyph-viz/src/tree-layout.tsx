import * as React from "react";
import { hierarchy, tree as d3tree, type HierarchyPointNode } from "d3-hierarchy";
import type { LayoutNode } from "@olik/glyph-schema";

export interface TreeLayoutProps {
  root: LayoutNode;
  width: number;
  height: number;
  nodeRadius?: number;
  linkColor?: string;
  renderNode: (node: LayoutNode) => React.ReactNode;
}

export function TreeLayout({
  root,
  width,
  height,
  linkColor = "#94a3b8",
  renderNode,
}: TreeLayoutProps): React.ReactElement {
  const layout = React.useMemo(() => {
    const h = hierarchy<LayoutNode>(root, (n) => n.children ?? []);
    return d3tree<LayoutNode>().size([width, height])(h);
  }, [root, width, height]);

  const nodes = layout.descendants();
  const links = layout.links();

  return (
    <g className="olik-tree">
      {links.map((l, i) => (
        <path
          key={`l${i}`}
          className="olik-tree-link"
          d={curveD(l.source, l.target)}
          fill="none"
          stroke={linkColor}
          strokeWidth={1.5}
        />
      ))}
      {nodes.map((n) => (
        <g key={n.data.id} className="olik-tree-node" transform={`translate(${n.x}, ${n.y})`}>
          {renderNode(n.data)}
        </g>
      ))}
    </g>
  );
}

function curveD(
  a: HierarchyPointNode<LayoutNode>,
  b: HierarchyPointNode<LayoutNode>,
): string {
  const mx = (a.y + b.y) / 2;
  return `M ${a.x} ${a.y} C ${a.x} ${mx}, ${b.x} ${mx}, ${b.x} ${b.y}`;
}
