import type { LayoutNode, Prototype } from "@olik/glyph-schema";

export interface PrototypeNodeData {
  prototype: Prototype;
  instanceCount: number;
  hostingChars: readonly string[];
}

export interface DecompNodeData {
  char: string;
  operator: string | null;
  components: readonly string[];
  wouldMode?: "keep" | "refine" | "replace";
  ruleId?: string;
}

export interface PlacementNodeData {
  node: LayoutNode;
}

export const NODE_TYPE_KEYS = {
  prototype: "olik-prototype",
  decomp: "olik-decomp",
  placement: "olik-placement",
} as const;
