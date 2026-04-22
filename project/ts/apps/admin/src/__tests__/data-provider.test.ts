import { describe, it, expect, vi } from "vitest";

import { createDataProvider } from "../data-provider.js";
import type { OlikDb, GlyphSummary } from "@olik/glyph-db";

function mockDb(): OlikDb {
  return {
    listGlyphs: vi.fn(async () => ({
      items: [
        { char: "林", stroke_count: 8, radical: "木", iou_mean: 0.83 } as GlyphSummary,
      ],
    })),
    getGlyph: vi.fn(async () => ({ char: "林", status: "needs_review" } as any)),
    listPrototypes: vi.fn(async () => []),
    getPrototypeUsers: vi.fn(async () => []),
    listVariants: vi.fn(async () => []),
    subscribeVariants: vi.fn(async () => async () => {}),
    updateGlyphStatus: vi.fn(async () => {}),
    close: vi.fn(async () => {}),
  };
}

describe("createDataProvider", () => {
  it("maps getList('glyph') to db.listGlyphs with translated filters", async () => {
    const db = mockDb();
    const dp = createDataProvider(db);
    const result = await dp.getList({
      resource: "glyph",
      filters: [
        { field: "status", operator: "in", value: ["needs_review"] },
        { field: "iou_mean", operator: "between", value: [0.5, 0.9] },
      ],
      sorters: [{ field: "iou_mean", order: "desc" }],
      pagination: { current: 1, pageSize: 50 },
    });
    expect(db.listGlyphs).toHaveBeenCalledWith(
      expect.objectContaining({
        filter: expect.objectContaining({
          status: ["needs_review"],
          iouRange: [0.5, 0.9],
        }),
        sort: "iou_mean",
        pageSize: 50,
      }),
    );
    expect(result.data).toHaveLength(1);
  });

  it("maps getOne('glyph', char) to db.getGlyph", async () => {
    const db = mockDb();
    const dp = createDataProvider(db);
    const result = await dp.getOne({ resource: "glyph", id: "林" });
    expect(db.getGlyph).toHaveBeenCalledWith("林");
    expect(result.data).toMatchObject({ char: "林" });
  });

  it("maps update('glyph', {status, review_note}) to db.updateGlyphStatus", async () => {
    const db = mockDb();
    const dp = createDataProvider(db);
    await dp.update({
      resource: "glyph",
      id: "林",
      variables: { status: "verified", review_note: "lgtm" },
    });
    expect(db.updateGlyphStatus).toHaveBeenCalledWith(
      "林",
      expect.objectContaining({ newStatus: "verified", reviewNote: "lgtm" }),
    );
  });

  it("returns an empty list for style_variant (Plan 11 stub)", async () => {
    const db = mockDb();
    const dp = createDataProvider(db);
    const result = await dp.getList({
      resource: "style_variant",
      pagination: { current: 1, pageSize: 50 },
    });
    expect(result).toEqual({ data: [], total: 0 });
  });

  it("throws on unsupported operations", async () => {
    const db = mockDb();
    const dp = createDataProvider(db);
    await expect(
      dp.create({ resource: "glyph", variables: {} }),
    ).rejects.toThrow(/not supported/i);
    await expect(
      dp.deleteOne({ resource: "glyph", id: "林" }),
    ).rejects.toThrow(/not supported/i);
  });
});
