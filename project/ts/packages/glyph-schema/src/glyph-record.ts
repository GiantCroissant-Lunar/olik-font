import { z } from "zod";
import { Affine } from "./affine.js";
import { Constraint } from "./constraint.js";
import { CoordSpace } from "./coord-space.js";
import { LayoutNode } from "./layout-tree.js";
import { DongChineseRole } from "./prototype.js";
import { StrokeInstance } from "./stroke-instance.js";

export const ComponentInstance = z
  .object({
    id: z.string(),
    prototype_ref: z.string().regex(/^proto:[A-Za-z0-9_]+$/),
    transform: Affine,
    placed_bbox: z.tuple([z.number(), z.number(), z.number(), z.number()]).optional(),
    style_slots: z.record(z.unknown()).optional(),
  })
  .strict();
export type ComponentInstance = z.infer<typeof ComponentInstance>;

export const RenderLayer = z
  .object({
    name: z.string(),
    z_min: z.number().int().min(0).max(99),
    z_max: z.number().int().min(0).max(99),
  })
  .strict();
export type RenderLayer = z.infer<typeof RenderLayer>;

export const IouReport = z
  .object({
    mean: z.number(),
    min: z.number(),
    per_stroke: z.record(z.number()).optional(),
    note: z.string().optional(),
  })
  .passthrough();
export type IouReport = z.infer<typeof IouReport>;

export const GlyphRecord = z
  .object({
    schema_version: z.string().regex(/^\d+\.\d+(\.\d+)?$/),
    glyph_id: z.string().min(1),
    unicode: z.string().regex(/^U\+[0-9A-F]{4,6}$/).optional(),
    coord_space: CoordSpace,
    source: z.record(z.unknown()).optional(),
    layout_tree: LayoutNode,
    component_instances: z.array(ComponentInstance),
    stroke_instances: z.array(StrokeInstance),
    mmh_strokes: z.array(z.string()).optional(),
    constraints: z.array(Constraint),
    render_layers: z.array(RenderLayer),
    roles: z.record(
      z
        .object({
          dong_chinese: DongChineseRole.optional(),
        })
        .passthrough(),
    ),
    metadata: z
      .object({
        generated_at: z.string().optional(),
        generator: z.string().optional(),
        iou_report: IouReport.optional(),
      })
      .passthrough(),
  })
  .strict();
export type GlyphRecord = z.infer<typeof GlyphRecord>;
