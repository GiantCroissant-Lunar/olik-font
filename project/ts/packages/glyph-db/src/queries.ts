import { Uuid, type Surreal } from "surrealdb";

import type { GlyphRecord } from "@olik/glyph-schema";
import type { OlikDb } from "./client.js";
import type { Unsubscribe } from "./types.js";
import {
  InvalidTransition,
  VALID_TRANSITIONS,
  type GlyphSummary,
  type ListOpts,
  type ListPage,
  type PrototypeSummary,
  type ReviewUpdate,
  type Status,
  type StyleVariant,
} from "./types.js";

type GlyphSortField = NonNullable<ListOpts["sort"]>;

export function buildListQuery(opts: ListOpts | undefined) {
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
  if (f.iouRange !== undefined) {
    clauses.push("iou_mean >= $iou_lo AND iou_mean <= $iou_hi");
    bind.iou_lo = f.iouRange[0];
    bind.iou_hi = f.iouRange[1];
  }
  if (f.status !== undefined) {
    clauses.push("status IN $status");
    bind.status = Array.isArray(f.status) ? f.status : [f.status];
  }
  const where = clauses.length > 0 ? ` WHERE ${clauses.join(" AND ")}` : "";

  const sortField: GlyphSortField = opts?.sort ?? "char";
  const order = opts?.order === "desc" ? "DESC" : "ASC";
  const comparator = order === "DESC" ? "<" : ">";
  const limit = opts?.pageSize ?? 50;
  let cursorClause = "";
  if (opts?.cursor !== undefined) {
    cursorClause = clauses.length > 0
      ? ` AND ${sortField} ${comparator} $cursor`
      : ` WHERE ${sortField} ${comparator} $cursor`;
    bind.cursor =
      sortField === "stroke_count" || sortField === "iou_mean"
        ? Number(opts.cursor)
        : opts.cursor;
  }
  const sql =
    "SELECT char, stroke_count, radical, iou_mean FROM glyph"
    + where
    + cursorClause
    + ` ORDER BY ${sortField} ${order} LIMIT ${limit + 1};`;

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
      const lastItem = items[items.length - 1];
      const nextCursor = hasMore
        ? String(lastItem[sortField])
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
      if (liveId === undefined) {
        throw new Error("LIVE SELECT did not return a subscription id");
      }
      const live = await raw.liveOf(new Uuid(liveId));
      const unsubscribe = live.subscribe((message) => {
        if (message.action === "CREATE" || message.action === "UPDATE") {
          cb(message.value as unknown as StyleVariant);
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
    async updateGlyphStatus(char: string, update: ReviewUpdate): Promise<void> {
      const [rows = []] = await raw
        .query("SELECT * FROM glyph WHERE char = $c;", { c: char })
        .collect<[Array<{ status?: string }>]>();
      const existing = rows[0];
      if (existing === undefined) {
        throw new Error(`glyph not found: ${char}`);
      }
      const currentStatus = (existing.status ?? "needs_review") as Status;
      if (!VALID_TRANSITIONS[currentStatus]?.has(update.newStatus)) {
        throw new InvalidTransition(currentStatus, update.newStatus);
      }
      await raw
        .query(
          "UPDATE type::record('glyph', $char) MERGE $patch;",
          {
            char,
            patch: {
              status: update.newStatus,
              review_note: update.reviewNote ?? null,
              reviewed_at: new Date().toISOString(),
              reviewed_by: update.reviewedBy ?? "browser",
            },
          },
        )
        .collect();
    },
    async close(): Promise<void> {
      await raw.close();
    },
  };
}
