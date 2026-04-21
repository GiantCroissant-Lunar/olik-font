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
  direct: "#6366f1",
  "preset:left_right": "#0ea5e9",
  "preset:top_bottom": "#14b8a6",
  "preset:enclose": "#d97706",
  "direct:repeat_triangle": "#a855f7",
  "anchor-binding": "#ec4899",
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
