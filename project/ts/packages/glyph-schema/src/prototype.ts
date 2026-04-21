import { z } from "zod";
import { BBox, Point } from "./coord-space.js";

export const StrokeRole = z.enum([
  "horizontal",
  "vertical",
  "dot",
  "hook",
  "slash",
  "backslash",
  "fold",
  "other",
]);
export type StrokeRole = z.infer<typeof StrokeRole>;

export const DongChineseRole = z.enum([
  "meaning",
  "sound",
  "iconic",
  "distinguishing",
  "unknown",
]);
export type DongChineseRole = z.infer<typeof DongChineseRole>;

export const RefinementMode = z.enum(["keep", "refine", "replace"]);
export type RefinementMode = z.infer<typeof RefinementMode>;

export const Stroke = z
  .object({
    id: z.string(),
    path: z.string(),
    median: z.array(Point),
    order: z.number().int().min(0),
    role: StrokeRole,
  })
  .strict();
export type Stroke = z.infer<typeof Stroke>;

export const Prototype = z
  .object({
    id: z.string().regex(/^proto:[A-Za-z0-9_]+$/),
    name: z.string(),
    kind: z.enum(["component", "stroke", "group"]),
    source: z.record(z.unknown()).optional(),
    canonical_bbox: BBox,
    strokes: z.array(Stroke),
    anchors: z.record(Point),
    roles: z.array(DongChineseRole).optional(),
    refinement: z.object({
      mode: RefinementMode,
      alternates: z.array(z.string()).optional(),
    }),
  })
  .strict();
export type Prototype = z.infer<typeof Prototype>;
