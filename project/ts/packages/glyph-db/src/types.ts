import type { GlyphRecord, Prototype } from "@olik/glyph-schema";

export type Status =
  | "verified"
  | "needs_review"
  | "unsupported_op"
  | "failed_extraction";

export const STATUS_VALUES: readonly Status[] = [
  "verified",
  "needs_review",
  "unsupported_op",
  "failed_extraction",
] as const;

export interface ReviewUpdate {
  newStatus: Status;
  reviewNote?: string | null;
  reviewedBy?: string;
}

export class InvalidTransition extends Error {
  constructor(public readonly from: Status, public readonly to: Status) {
    super(`invalid status transition: ${from} -> ${to}`);
    this.name = "InvalidTransition";
  }
}

/**
 * Mirrors `olik_font.bulk.status.Status.VALID_TRANSITIONS` semantics.
 * Plan 09.1 permits every transition; Plan 10's UI only issues
 * `needs_review -> verified|failed_extraction`, but client-side
 * enforcement is strict so future UI paths can't silently regress.
 * Self-transitions are included so idempotent writes don't throw.
 */
export const VALID_TRANSITIONS: Record<Status, ReadonlySet<Status>> = {
  verified: new Set(["verified", "needs_review", "failed_extraction"]),
  needs_review: new Set(["verified", "needs_review", "failed_extraction"]),
  unsupported_op: new Set([
    "verified",
    "needs_review",
    "failed_extraction",
    "unsupported_op",
  ]),
  failed_extraction: new Set([
    "verified",
    "needs_review",
    "failed_extraction",
    "unsupported_op",
  ]),
};

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
  iouRange?: [number, number];
  status?: Status | Status[];
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
