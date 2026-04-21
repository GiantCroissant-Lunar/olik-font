import { describe, expect, test } from "vitest";
import { resolve } from "node:path";
import { existsSync, writeFileSync, mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { loadGlyphRecord, loadPrototypeLibrary, loadRuleTrace } from "../src/load-fs.js";

const EXAMPLES = resolve(__dirname, "../../../../schema/examples");

describe("load-fs", () => {
  test("loads hello-library.json", async () => {
    const path = resolve(EXAMPLES, "hello-library.json");
    const lib = await loadPrototypeLibrary(path);
    expect(lib.prototypes["proto:hello"]).toBeDefined();
  });

  test("loads hello-record.json", async () => {
    const path = resolve(EXAMPLES, "hello-record.json");
    const rec = await loadGlyphRecord(path);
    expect(rec.glyph_id).toBe("hello");
  });

  test("throws on validation failure", async () => {
    const dir = mkdtempSync(resolve(tmpdir(), "olik-test-"));
    const bad = resolve(dir, "bad.json");
    writeFileSync(bad, JSON.stringify({ glyph_id: "x" }));
    await expect(loadGlyphRecord(bad)).rejects.toThrow();
  });

  test("throws when file doesn't exist", async () => {
    await expect(loadGlyphRecord("/nonexistent")).rejects.toThrow();
  });

  test("loads a real rule trace if CLI has been run", async () => {
    const path = resolve(EXAMPLES, "rule-trace-明.json");
    if (!existsSync(path)) return;
    const trace = await loadRuleTrace(path);
    expect(trace.decisions.length).toBeGreaterThan(0);
  });
});
