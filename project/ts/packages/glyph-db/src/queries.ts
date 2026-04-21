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

function buildListQuery(opts: ListOpts | undefined) {
  const clauses: string[] = [];
  const bind: Record<string, unknown> = {};
  const f = opts?.filter ?? {};
  if (f.radical !== undefined) {
    clauses.push("radical = $rad");
    bind.rad = f.radical;
  }
  if (f.strokeCountRange !== undefined) {
    clauses.push("stroke_count >= $lo AND stroke_count <= $hi");
    bind.lo = f.strokeCountRange[0];
    bind.hi = f.strokeCountRange[1];
  }
  if (f.iouBelow !== undefined) {
    clauses.push("iou_mean < $iou");
    bind.iou = f.iouBelow;
  }
  const where = clauses.length > 0 ? ` WHERE ${clauses.join(" AND ")}` : "";

  const sortField = opts?.sort ?? "char";
  const limit = opts?.pageSize ?? 50;
  let cursorClause = "";
  if (opts?.cursor !== undefined) {
    cursorClause = clauses.length > 0 ? ` AND ${sortField} > $cursor` : ` WHERE ${sortField} > $cursor`;
    bind.cursor =
      sortField === "stroke_count" || sortField === "iou_mean"
        ? Number(opts.cursor)
        : opts.cursor;
  }
  const sql =
    "SELECT char, stroke_count, radical, iou_mean FROM glyph"
    + where
    + cursorClause
    + ` ORDER BY ${sortField} LIMIT ${limit + 1};`;

  return { sql, bind, limit, sortField };
}

export function makeQueries(raw: Surreal): OlikDb {
  return {
    async listGlyphs(opts?: ListOpts): Promise<ListPage<GlyphSummary>> {
      const { sql, bind, limit, sortField } = buildListQuery(opts);
      const [rows = []] = await raw
        .query(sql, bind)
        .collect<[GlyphSummary[]]>();
      const hasMore = rows.length > limit;
      const items = hasMore ? rows.slice(0, limit) : rows;
      const nextCursor = hasMore
        ? String((items[items.length - 1] as Record<string, unknown>)[sortField])
        : undefined;
      return { items, nextCursor };
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
    async getPrototypeUsers(id: string): Promise<GlyphSummary[]> {
      const [rows = []] = await raw
        .query(
          "SELECT char, stroke_count, radical, iou_mean FROM glyph "
            + "WHERE id IN (SELECT VALUE in FROM uses WHERE out = type::record('prototype', $id)) "
            + "ORDER BY char;",
          { id },
        )
        .collect<[GlyphSummary[]]>();
      return rows;
    },
    async listVariants(char: string): Promise<StyleVariant[]> {
      const [rows = []] = await raw
        .query<StyleVariant[]>(
          "SELECT char, style_name, image_ref, workflow_id, status, generated_at "
            + "FROM style_variant WHERE char = $c ORDER BY generated_at;",
          { c: char },
        )
        .collect<[StyleVariant[]]>();
      return rows;
    },
    async subscribeVariants(
      char: string,
      cb: (v: StyleVariant) => void,
    ): Promise<Unsubscribe> {
      const [liveId] = await raw
        .query<[string]>(
          "LIVE SELECT * FROM style_variant WHERE char = $c;",
          { c: char },
        )
        .collect<[string]>();
      const live = await raw.liveOf(liveId);
      const unsubscribe = live.subscribe((message) => {
        if (message.action === "CREATE" || message.action === "UPDATE") {
          cb(message.value as StyleVariant);
        }
      });
      return async () => {
        unsubscribe();
        try {
          await live.kill();
        } catch {
          // connection may already be closed
        }
      };
    },
    async close(): Promise<void> {
      await raw.close();
    },
  };
}
