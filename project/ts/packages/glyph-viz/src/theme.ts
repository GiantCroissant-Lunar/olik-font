export const GLYPH_CANVAS_SIZE = 1024;

export const STROKE_COLOR = {
  outline: "#1f2937",
  median: "#f97316",
  highlight: "#10b981",
} as const;

export const LAYER_COLOR: Record<string, string> = {
  skeleton: "#9ca3af",
  stroke_body: "#111827",
  stroke_edge: "#6366f1",
  texture_overlay: "#ec4899",
  damage: "#dc2626",
};

export const INPUT_ADAPTER_COLOR: Record<string, string> = {
  extraction_plan: "#6366f1",
  refine: "#0ea5e9",
  measured: "#14b8a6",
  leaf: "#64748b",
};

export const IOU_THRESHOLD = {
  warn: 0.85,
  fail: 0.80,
} as const;

export function iouColor(v: number): string {
  if (v >= IOU_THRESHOLD.warn) return "#10b981";
  if (v >= IOU_THRESHOLD.fail) return "#eab308";
  return "#dc2626";
}
