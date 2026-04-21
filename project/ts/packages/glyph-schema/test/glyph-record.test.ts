import { describe, expect, test } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { GlyphRecord } from "../src/glyph-record.js";

const helloPath = resolve(
  __dirname,
  "../../../../schema/examples/hello-record.json",
);

describe("GlyphRecord", () => {
  test("hello example validates", () => {
    const raw = JSON.parse(readFileSync(helloPath, "utf-8"));
    const parsed = GlyphRecord.parse(raw);
    expect(parsed.glyph_id).toBe("hello");
  });

  test("rejects record missing render_layers", () => {
    const raw = JSON.parse(readFileSync(helloPath, "utf-8"));
    delete raw.render_layers;
    expect(() => GlyphRecord.parse(raw)).toThrow();
  });

  test("discriminated union accepts a left_right-style constraint list", () => {
    const raw = JSON.parse(readFileSync(helloPath, "utf-8"));
    raw.constraints = [
      { kind: "align_y", targets: ["inst:a.center", "inst:b.center"] },
      { kind: "order_x", before: "inst:a", after: "inst:b" },
      {
        kind: "anchor_distance",
        from: "inst:a.right_edge",
        to: "inst:b.left_edge",
        value: 20,
      },
    ];
    const parsed = GlyphRecord.parse(raw);
    expect(parsed.constraints).toHaveLength(3);
  });

  test("rejects unknown constraint kind", () => {
    const raw = JSON.parse(readFileSync(helloPath, "utf-8"));
    raw.constraints = [{ kind: "not_a_constraint" }];
    expect(() => GlyphRecord.parse(raw)).toThrow();
  });
});
