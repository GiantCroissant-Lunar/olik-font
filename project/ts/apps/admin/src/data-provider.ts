import type { DataProvider, CrudFilter, CrudSort } from "@refinedev/core";
import type { OlikDb, GlyphSummary, ListFilter, Status } from "@olik/glyph-db";

function mapFilters(filters: CrudFilter[] | undefined): ListFilter {
  const out: ListFilter = {};
  for (const f of filters ?? []) {
    if (!("field" in f)) continue;
    switch (f.field) {
      case "status":
        if (f.operator === "eq" || f.operator === "in") {
          out.status = Array.isArray(f.value)
            ? (f.value as Status[])
            : (f.value as Status);
        }
        break;
      case "iou_mean":
        if (f.operator === "between" && Array.isArray(f.value)) {
          out.iouRange = [Number(f.value[0]), Number(f.value[1])];
        } else if (f.operator === "lt") {
          out.iouBelow = Number(f.value);
        }
        break;
      case "stroke_count":
        if (f.operator === "between" && Array.isArray(f.value)) {
          out.strokeCountRange = [Number(f.value[0]), Number(f.value[1])];
        }
        break;
      case "radical":
        if (f.operator === "eq") {
          out.radical = String(f.value);
        }
        break;
      default:
        if (typeof console !== "undefined") {
          console.warn("data-provider: unsupported filter", f);
        }
    }
  }
  return out;
}

function mapSort(
  sorters: CrudSort[] | undefined,
): "char" | "stroke_count" | "iou_mean" {
  const s = sorters?.[0];
  if (s?.field === "stroke_count") return "stroke_count";
  if (s?.field === "iou_mean") return "iou_mean";
  return "char";
}

export function createDataProvider(db: OlikDb): DataProvider {
  const notSupported = (op: string) =>
    Promise.reject(new Error(`${op} is not supported in Plan 10`));

  return {
    getList: async ({ resource, filters, sorters, pagination }) => {
      if (resource === "style_variant") {
        return { data: [], total: 0 };
      }
      if (resource !== "glyph") {
        throw new Error(`unknown resource: ${resource}`);
      }
      const page = await db.listGlyphs({
        filter: mapFilters(filters),
        sort: mapSort(sorters),
        pageSize: pagination?.pageSize ?? 50,
      });
      return {
        data: page.items as unknown as GlyphSummary[],
        total: page.items.length,
      };
    },
    getOne: async ({ resource, id }) => {
      if (resource !== "glyph") throw new Error("getOne only supported for glyph");
      const row = await db.getGlyph(String(id));
      if (row === null) throw new Error(`glyph not found: ${id}`);
      return { data: { ...(row as any), id: (row as any).char } as any };
    },
    update: async ({ resource, id, variables }) => {
      if (resource !== "glyph") throw new Error("update only supported for glyph");
      const v = variables as { status?: Status; review_note?: string | null };
      if (!v.status) throw new Error("update requires { status }");
      await db.updateGlyphStatus(String(id), {
        newStatus: v.status,
        reviewNote: v.review_note ?? null,
        reviewedBy: currentUser(),
      });
      const row = await db.getGlyph(String(id));
      return { data: { ...row, id: String(id) } as any };
    },
    create: () => notSupported("create"),
    deleteOne: () => notSupported("deleteOne"),
    updateMany: () => notSupported("updateMany"),
    custom: () => notSupported("custom"),
    getApiUrl: () => "olik://surrealdb",
    getMany: async ({ resource, ids }) => {
      if (resource !== "glyph") throw new Error("getMany only supported for glyph");
      const rows = await Promise.all(ids.map((id) => db.getGlyph(String(id))));
      return {
        data: rows
          .filter((r) => r !== null)
          .map((r) => ({ ...(r as any), id: (r as any).char })) as any[],
      };
    },
  } as DataProvider;
}

function currentUser(): string {
  const env = (import.meta as ImportMeta & { env?: { VITE_REVIEWER?: string } }).env;
  return env?.VITE_REVIEWER ?? "browser";
}
