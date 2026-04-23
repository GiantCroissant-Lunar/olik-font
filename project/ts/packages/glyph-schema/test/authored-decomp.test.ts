import { describe, expect, test } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { AuthoredDecomposition } from "../src/authored-decomp.js";

const samplePath = resolve(
  __dirname,
  "../../../../py/data/glyph_decomp/丁.json",
);

describe("AuthoredDecomposition", () => {
  test("sample authored override validates", () => {
    const raw = JSON.parse(readFileSync(samplePath, "utf-8"));
    const parsed = AuthoredDecomposition.parse(raw);

    expect(parsed.char).toBe("丁");
    expect(parsed.supersedes).toBe("mmh");
    expect(parsed.partition).toHaveLength(2);
  });
});
