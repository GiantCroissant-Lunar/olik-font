// Minimal local types matching the JSON shape of glyph-record-*.json.
// Intentionally NOT importing from @olik/glyph-schema (which doesn't exist
// yet — Plan 04 builds it). Once Plan 04 lands we'll switch to those.

export type Point = [number, number];
export type BBox = [number, number, number, number];

export interface StrokeInstance {
  id: string;
  instance_id: string;
  order: number;
  path: string;
  median: Point[];
  bbox: BBox;
  z: number;
  role: string;
}

export interface LayoutNode {
  id: string;
  bbox: BBox;
  prototype_ref?: string;
  mode?: "keep" | "refine" | "replace";
  depth?: number;
  input_adapter?: string;
  children?: LayoutNode[];
}

export interface IouReport {
  mean: number;
  min: number;
  per_stroke?: Record<string, number>;
  note?: string;
}

export interface GlyphRecord {
  schema_version: string;
  glyph_id: string;
  unicode?: string;
  coord_space: { width: number; height: number; origin: string; y_axis: string };
  layout_tree: LayoutNode;
  stroke_instances: StrokeInstance[];
  metadata?: { iou_report?: IouReport };
}
