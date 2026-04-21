import type { GlyphRecord, Prototype } from "@olik/glyph-schema";

export interface GlyphSummary {
  char: string;
  stroke_count: number;
  radical: string | null;
  iou_mean: number;
}

export interface PrototypeSummary {
  id: string;
  name: string;
  usage_count?: number;
}

export interface StyleVariant {
  char: string;
  style_name: string;
  image_ref: string;
  workflow_id?: string;
  status: "queued" | "running" | "done" | "failed";
  generated_at?: string;
}

export type ListFilter = {
  radical?: string;
  strokeCountRange?: [number, number];
  iouBelow?: number;
};

export interface ListOpts {
  filter?: ListFilter;
  sort?: "char" | "stroke_count" | "iou_mean";
  pageSize?: number;
  cursor?: string;
}

export interface ListPage<T> {
  items: T[];
  nextCursor?: string;
}

export type Unsubscribe = () => Promise<void>;

export type { GlyphRecord, Prototype };
