import type { LayoutNode, Prototype } from "@olik/glyph-schema";

export interface PrototypeNodeData extends Record<string, unknown> {
  prototype: Prototype;
  instanceCount: number;
  hostingChars: readonly string[];
}

export type DecompNodeTone = "leaf" | "measured" | "refine" | "replaced";

export interface DecompNodeData extends Record<string, unknown> {
  char: string;
  operator: string | null;
  components: readonly string[];
  wouldMode?: "keep" | "refine" | "replace";
  ruleId?: string;
  sourceBadge?: string | null;
  tone?: DecompNodeTone;
}

export interface PlacementNodeData extends Record<string, unknown> {
  node: LayoutNode;
}

export const NODE_TYPE_KEYS = {
  prototype: "olik-prototype",
  decomp: "olik-decomp",
  placement: "olik-placement",
} as const;
