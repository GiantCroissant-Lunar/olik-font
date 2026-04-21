import { z } from "zod";
import { CoordSpace } from "./coord-space.js";
import { Prototype } from "./prototype.js";

export const LibraryEdge = z
  .object({
    from: z.string(),
    kind: z.enum(["refines-to", "replaces"]),
    to: z.string(),
  })
  .strict();
export type LibraryEdge = z.infer<typeof LibraryEdge>;

export const PrototypeLibrary = z
  .object({
    schema_version: z.string().regex(/^\d+\.\d+(\.\d+)?$/),
    coord_space: CoordSpace,
    prototypes: z.record(
      z.string().regex(/^proto:[A-Za-z0-9_]+$/),
      Prototype,
    ),
    edges: z.array(LibraryEdge).optional(),
  })
  .strict();
export type PrototypeLibrary = z.infer<typeof PrototypeLibrary>;
