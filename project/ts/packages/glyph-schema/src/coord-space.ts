import { z } from "zod";

export const CoordSpace = z.object({
  width: z.literal(1024),
  height: z.literal(1024),
  origin: z.literal("top-left"),
  y_axis: z.literal("down"),
}).strict();

export type CoordSpace = z.infer<typeof CoordSpace>;

export const CANONICAL_COORD_SPACE: CoordSpace = {
  width: 1024,
  height: 1024,
  origin: "top-left",
  y_axis: "down",
};

export const Point = z.tuple([z.number(), z.number()]);
export type Point = z.infer<typeof Point>;

export const BBox = z.tuple([z.number(), z.number(), z.number(), z.number()]);
export type BBox = z.infer<typeof BBox>;
