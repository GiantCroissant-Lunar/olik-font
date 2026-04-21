import { existsSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, test } from "vitest";
import { loadBundleFs } from "../src/bundle.js";

const EXAMPLES = resolve(__dirname, "../../../../schema/examples");

describe.runIf(existsSync(resolve(EXAMPLES, "prototype-library.json")))(
  "loadBundleFs",
  () => {
    test("loads all 4 seed records + library + traces", async () => {
      const chars = ["明", "清", "國", "森"] as const;
      const bundle = await loadBundleFs(EXAMPLES, chars);
      expect(Object.keys(bundle.library.prototypes).length).toBeGreaterThanOrEqual(7);
      for (const ch of chars) {
        expect(bundle.records[ch].glyph_id).toBe(ch);
        expect(bundle.traces[ch].decisions.length).toBeGreaterThan(0);
      }
    });

    test("missing file throws", async () => {
      await expect(loadBundleFs(EXAMPLES, ["not-a-char"])).rejects.toThrow();
    });
  },
);
