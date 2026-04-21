import * as React from "react";
import { AbsoluteFill } from "remotion";
import { GraphLayout, type GraphLink, type GraphNode } from "@olik/glyph-viz";
import type { GlyphBundle } from "@olik/glyph-loader";

export interface PrototypeGraphProps extends Record<string, unknown> {
  bundle: GlyphBundle;
  highlightChar?: string;
}

export const PrototypeGraph: React.FC<PrototypeGraphProps> = ({
  bundle, highlightChar,
}) => {
  const protoIds = Object.keys(bundle.library.prototypes);
  const cx = 640;
  const cy = 360;
  const r = 220;
  const nodes: GraphNode[] = protoIds.map((id, i) => {
    const a = (i / protoIds.length) * Math.PI * 2;
    return { id, x: cx + r * Math.cos(a), y: cy + r * Math.sin(a) };
  });

  const chars = Object.keys(bundle.records);
  const outerRadius = 340;
  const charNodes: GraphNode[] = chars.map((ch, i) => {
    const a = (i / chars.length) * Math.PI * 2 + Math.PI / chars.length;
    return { id: `char:${ch}`, x: cx + outerRadius * Math.cos(a), y: cy + outerRadius * Math.sin(a) };
  });

  const links: GraphLink[] = [];
  for (const ch of chars) {
    const rec = bundle.records[ch];
    if (!rec) continue;
    const used = new Set<string>();
    for (const inst of rec.component_instances) {
      used.add(inst.prototype_ref);
    }
    for (const p of used) {
      links.push({
        source: `char:${ch}`,
        target: p,
        kind: ch === highlightChar ? "highlight" : "used-by",
      });
    }
  }

  return (
    <AbsoluteFill style={{ background: "#ffffff" }}>
      <svg width={1280} height={720}>
        <GraphLayout
          nodes={[...nodes, ...charNodes]}
          links={links}
          linkColor="#cbd5e1"
          renderNode={(n) => {
            const isChar = n.id.startsWith("char:");
            if (isChar) {
              return (
                <text
                  textAnchor="middle"
                  dy={6}
                  fontSize={28}
                  fontFamily="serif"
                  fill={highlightChar && n.id === `char:${highlightChar}` ? "#10b981" : "#0f172a"}
                >
                  {n.id.slice(5)}
                </text>
              );
            }

            return (
              <>
                <circle r={14} fill="#f8fafc" stroke="#475569" />
                <text textAnchor="middle" dy={4} fontSize={11} fontFamily="monospace">
                  {bundle.library.prototypes[n.id]?.name ?? ""}
                </text>
              </>
            );
          }}
        />
      </svg>
    </AbsoluteFill>
  );
};
