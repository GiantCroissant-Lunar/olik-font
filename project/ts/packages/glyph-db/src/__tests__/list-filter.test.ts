import { describe, it, expect } from "vitest";
import { buildListQuery } from "../queries.js";

describe("buildListQuery", () => {
  it("includes status clause when filter.status is a single value", () => {
    const { sql, bind } = buildListQuery({ filter: { status: "needs_review" } });
    expect(sql).toContain("status IN $status");
    expect(bind.status).toEqual(["needs_review"]);
  });

  it("accepts status as an array of values", () => {
    const { sql, bind } = buildListQuery({
      filter: { status: ["needs_review", "failed_extraction"] },
    });
    expect(sql).toContain("status IN $status");
    expect(bind.status).toEqual(["needs_review", "failed_extraction"]);
  });

  it("applies iouRange as a between clause", () => {
    const { sql, bind } = buildListQuery({ filter: { iouRange: [0.5, 0.9] } });
    expect(sql).toContain("iou_mean >= $iou_lo AND iou_mean <= $iou_hi");
    expect(bind.iou_lo).toBe(0.5);
    expect(bind.iou_hi).toBe(0.9);
  });

  it("combines multiple filters with AND", () => {
    const { sql } = buildListQuery({
      filter: { status: "needs_review", iouRange: [0.5, 0.9], strokeCountRange: [5, 15] },
    });
    expect(sql).toMatch(/WHERE .+ AND .+ AND .+/);
  });

  it("keeps iouBelow back-compat working alongside iouRange", () => {
    const { sql, bind } = buildListQuery({ filter: { iouBelow: 0.75 } });
    expect(sql).toContain("iou_mean < $iou");
    expect(bind.iou).toBe(0.75);
  });
});
