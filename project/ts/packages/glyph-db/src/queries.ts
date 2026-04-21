import type { Surreal } from "surrealdb";

import type { GlyphRecord } from "@olik/glyph-schema";
import type { OlikDb } from "./client.js";
import type { Unsubscribe } from "./types.js";
import type {
  GlyphSummary,
  ListOpts,
  ListPage,
  PrototypeSummary,
  StyleVariant,
} from "./types.js";

export function makeQueries(raw: Surreal): OlikDb {
  return {
    async listGlyphs(_opts?: ListOpts): Promise<ListPage<GlyphSummary>> {
      const [rows = []] = await raw
        .query("SELECT char, stroke_count, radical, iou_mean FROM glyph ORDER BY char;")
        .collect<[GlyphSummary[]]>();
      return { items: rows };
    },
    async getGlyph(char: string): Promise<GlyphRecord | null> {
      const [rows = []] = await raw
        .query("SELECT * FROM glyph WHERE char = $c;", { c: char })
        .collect<[Array<GlyphRecord & { char?: string }>]>();
      return rows[0] ?? null;
    },
    async listPrototypes(): Promise<PrototypeSummary[]> {
      const [rows = []] = await raw
        .query("SELECT id, name, usage_count FROM prototype ORDER BY id;")
        .collect<[PrototypeSummary[]]>();
      return rows;
    },
    async getPrototypeUsers(_id: string): Promise<GlyphSummary[]> {
      return [];
    },
    async listVariants(_char: string): Promise<StyleVariant[]> {
      return [];
    },
    async subscribeVariants(
      _char: string,
      _cb: (v: StyleVariant) => void,
    ): Promise<Unsubscribe> {
      return async () => {};
    },
    async close(): Promise<void> {
      await raw.close();
    },
  };
}
