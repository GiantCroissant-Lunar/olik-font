import { z } from "zod";

export const AlignX = z
  .object({
    kind: z.literal("align_x"),
    targets: z.array(z.string()),
  })
  .strict();

export const AlignY = z
  .object({
    kind: z.literal("align_y"),
    targets: z.array(z.string()),
  })
  .strict();

export const OrderX = z
  .object({
    kind: z.literal("order_x"),
    before: z.string(),
    after: z.string(),
  })
  .strict();

export const OrderY = z
  .object({
    kind: z.literal("order_y"),
    above: z.string(),
    below: z.string(),
  })
  .strict();

export const AnchorDistance = z
  .object({
    kind: z.literal("anchor_distance"),
    from: z.string(),
    to: z.string(),
    value: z.number(),
  })
  .strict();

export const Inside = z
  .object({
    kind: z.literal("inside"),
    target: z.string(),
    frame: z.string(),
    padding: z.number(),
  })
  .strict();

export const AvoidOverlap = z
  .object({
    kind: z.literal("avoid_overlap"),
    a: z.string(),
    b: z.string(),
    padding: z.number(),
  })
  .strict();

export const Repeat = z
  .object({
    kind: z.literal("repeat"),
    prototype_ref: z.string(),
    count: z.number().int(),
    layout_hint: z.string(),
  })
  .strict();

export const Constraint = z.discriminatedUnion("kind", [
  AlignX,
  AlignY,
  OrderX,
  OrderY,
  AnchorDistance,
  Inside,
  AvoidOverlap,
  Repeat,
]);
export type Constraint = z.infer<typeof Constraint>;
