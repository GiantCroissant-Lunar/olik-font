import { z } from "zod";
import { Point } from "./coord-space.js";

export const Affine = z.object({
  translate: Point,
  scale: Point,
  rotate: z.number(),
  shear: Point,
}).strict();

export type Affine = z.infer<typeof Affine>;

export const IDENTITY_AFFINE: Affine = {
  translate: [0, 0],
  scale: [1, 1],
  rotate: 0,
  shear: [0, 0],
};
