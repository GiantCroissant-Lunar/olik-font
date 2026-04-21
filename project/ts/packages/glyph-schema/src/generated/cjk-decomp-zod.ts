import * as z from "zod";


export const EntrySchema = z.object({
    "components": z.array(z.string()),
    "operator": z.union([z.null(), z.string()]),
});
export type Entry = z.infer<typeof EntrySchema>;

export const SourceSchema = z.object({
    "commit": z.string(),
    "license": z.string(),
    "retrieved_at": z.coerce.date().optional(),
    "upstream": z.string(),
});
export type Source = z.infer<typeof SourceSchema>;

export const CjkDecompSchema = z.object({
    "entries": z.record(z.string(), EntrySchema),
    "schema_version": z.string(),
    "source": SourceSchema,
});
export type CjkDecomp = z.infer<typeof CjkDecompSchema>;
