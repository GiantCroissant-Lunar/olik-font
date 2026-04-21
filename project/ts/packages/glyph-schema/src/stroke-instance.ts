import { z } from "zod";
import { BBox, Point } from "./coord-space.js";

export const StrokeInstance = z
  .object({
    id: z.string(),
    instance_id: z.string(),
    order: z.number().int().min(0),
    path: z.string(),
    median: z.array(Point),
    bbox: BBox,
    z: z.number().int().min(0).max(99),
    role: z.string(),
  })
  .strict();
export type StrokeInstance = z.infer<typeof StrokeInstance>;
