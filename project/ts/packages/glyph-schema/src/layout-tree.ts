import { z } from "zod";
import { Affine } from "./affine.js";
import { BBox } from "./coord-space.js";
import { RefinementMode } from "./prototype.js";

export const AnchorBinding = z
  .object({
    from: z.string(),
    to: z.string(),
    distance: z.number().optional(),
  })
  .strict();
export type AnchorBinding = z.infer<typeof AnchorBinding>;

const baseNode = z
  .object({
    id: z.string(),
    prototype_ref: z.string().regex(/^proto:[A-Za-z0-9_]+$/).optional(),
    bbox: BBox,
    mode: RefinementMode.optional(),
    depth: z.number().int().min(0).optional(),
    transform: Affine.optional(),
    anchor_bindings: z.array(AnchorBinding).optional(),
    decomp_source: z.record(z.unknown()).optional(),
    input_adapter: z.string().optional(),
  })
  .strict();

export type LayoutNode = z.infer<typeof baseNode> & { children?: LayoutNode[] };

export const LayoutNode: z.ZodType<LayoutNode> = baseNode.extend({
  children: z.lazy(() => z.array(LayoutNode).optional()),
});
