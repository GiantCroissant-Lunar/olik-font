import { describe, expect, test } from "vitest";
import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import { GlyphRecord } from "../src/glyph-record.js";
import { PrototypeLibrary } from "../src/prototype-library.js";
import { RuleTrace } from "../src/rule-trace.js";

const EXAMPLES = resolve(__dirname, "../../../../schema/examples");
const SEED = ["明", "清", "國", "森"] as const;

describe.runIf(existsSync(resolve(EXAMPLES, "prototype-library.json")))(
  "validates real CLI outputs",
  () => {
    test("prototype-library.json validates", () => {
      const raw = JSON.parse(
        readFileSync(resolve(EXAMPLES, "prototype-library.json"), "utf-8"),
      );
      const parsed = PrototypeLibrary.parse(raw);
      expect(Object.keys(parsed.prototypes).length).toBeGreaterThanOrEqual(7);
    });

    for (const ch of SEED) {
      test(`glyph-record-${ch}.json validates`, () => {
        const path = resolve(EXAMPLES, `glyph-record-${ch}.json`);
        if (!existsSync(path)) return;
        const raw = JSON.parse(readFileSync(path, "utf-8"));
        const parsed = GlyphRecord.parse(raw);
        expect(parsed.glyph_id).toBe(ch);
        expect(parsed.stroke_instances.length).toBeGreaterThan(0);
      });

      test(`rule-trace-${ch}.json validates`, () => {
        const path = resolve(EXAMPLES, `rule-trace-${ch}.json`);
        if (!existsSync(path)) return;
        const raw = JSON.parse(readFileSync(path, "utf-8"));
        const parsed = RuleTrace.parse(raw);
        expect(parsed.decisions.length).toBeGreaterThan(0);
      });
    }
  },
);
