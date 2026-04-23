import { z } from "zod";
import { DongChineseRole } from "./prototype.js";

export const PrototypeGraphNodeKind = z.enum([
  "focus",
  "variant-parent",
  "variant-sibling",
  "child",
]);
export type PrototypeGraphNodeKind = z.infer<typeof PrototypeGraphNodeKind>;

export const PrototypeGraphRelation = z.enum(["variant_of", "decomposes_into"]);
export type PrototypeGraphRelation = z.infer<typeof PrototypeGraphRelation>;

export const PrototypeGraphGlyphCell = z
  .object({
    char: z.string().min(1),
    productive_count: z.number().int().nonnegative(),
  })
  .strict();
export type PrototypeGraphGlyphCell = z.infer<typeof PrototypeGraphGlyphCell>;

export const PrototypeGraphNode = z
  .object({
    id: z.string().min(1),
    label: z.string().min(1),
    kind: PrototypeGraphNodeKind,
    role: DongChineseRole.optional(),
    etymology: z.enum(["pictographic", "ideographic", "pictophonetic"]).nullable().optional(),
    productive_count: z.number().int().nonnegative().optional(),
  })
  .strict();
export type PrototypeGraphNode = z.infer<typeof PrototypeGraphNode>;

export const PrototypeGraphEdge = z
  .object({
    id: z.string().min(1),
    source: z.string().min(1),
    target: z.string().min(1),
    relation: PrototypeGraphRelation,
  })
  .strict();
export type PrototypeGraphEdge = z.infer<typeof PrototypeGraphEdge>;

export const PrototypeGraphSnapshot = z
  .object({
    schema_version: z.string().regex(/^\d+\.\d+(\.\d+)?$/),
    focus: PrototypeGraphNode.extend({
      kind: z.literal("focus"),
      role: DongChineseRole,
      etymology: z.enum(["pictographic", "ideographic", "pictophonetic"]).nullable(),
      productive_count: z.number().int().nonnegative(),
    }).strict(),
    nodes: z.array(PrototypeGraphNode),
    edges: z.array(PrototypeGraphEdge),
    appears_in: z.array(PrototypeGraphGlyphCell),
  })
  .strict()
  .superRefine((snapshot, ctx) => {
    const nodeIds = new Set(snapshot.nodes.map((node) => node.id));
    if (!nodeIds.has(snapshot.focus.id)) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["focus", "id"],
        message: "focus id must be present in nodes",
      });
    }
    for (const edge of snapshot.edges) {
      if (!nodeIds.has(edge.source) || !nodeIds.has(edge.target)) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          path: ["edges"],
          message: `edge ${edge.id} references unknown node`,
        });
      }
    }
  });
export type PrototypeGraphSnapshot = z.infer<typeof PrototypeGraphSnapshot>;
