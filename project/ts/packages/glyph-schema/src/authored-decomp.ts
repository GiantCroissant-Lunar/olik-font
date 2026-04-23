import { z } from "zod";
import { RefinementMode } from "./prototype.js";

const ProtoRef = z.string().regex(/^proto:[A-Za-z0-9_]+$/);

export const AuthoredPartitionNode: z.ZodType<{
  prototype_ref: string;
  mode?: z.infer<typeof RefinementMode>;
  source_stroke_indices?: number[];
  children?: z.infer<typeof AuthoredPartitionNode>[];
  replacement_proto_ref?: string;
}> = z.lazy(() =>
  z
    .object({
      prototype_ref: ProtoRef,
      mode: RefinementMode.default("keep"),
      source_stroke_indices: z.array(z.number().int().min(0)).min(1).optional(),
      children: z.array(AuthoredPartitionNode).default([]),
      replacement_proto_ref: ProtoRef.optional(),
    })
    .strict()
    .superRefine((value, ctx) => {
      if (value.mode === "replace" && value.replacement_proto_ref === undefined) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: "replacement_proto_ref is required when mode='replace'",
          path: ["replacement_proto_ref"],
        });
      }
      if (value.mode !== "replace" && value.replacement_proto_ref !== undefined) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: "replacement_proto_ref is only allowed when mode='replace'",
          path: ["replacement_proto_ref"],
        });
      }
    }),
);
export type AuthoredPartitionNode = z.infer<typeof AuthoredPartitionNode>;

export const AuthoredDecomposition = z
  .object({
    schema_version: z.literal("0.1"),
    char: z.string().length(1),
    supersedes: z.enum(["mmh", "animcjk", "cjk-decomp"]),
    rationale: z.string().min(1),
    authored_by: z.string().min(1),
    authored_at: z.string().datetime({ offset: true }),
    partition: z.array(AuthoredPartitionNode).min(1),
  })
  .strict();
export type AuthoredDecomposition = z.infer<typeof AuthoredDecomposition>;
