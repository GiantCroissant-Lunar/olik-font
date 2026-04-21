import { resolve } from "node:path";
import type { GlyphRecord, PrototypeLibrary, RuleTrace } from "@olik/glyph-schema";
import { loadGlyphRecord, loadPrototypeLibrary, loadRuleTrace } from "./load-fs.js";

export interface GlyphBundle {
  library: PrototypeLibrary;
  records: Record<string, GlyphRecord>;
  traces: Record<string, RuleTrace>;
}

export async function loadBundleFs(
  examplesDir: string,
  chars: readonly string[],
): Promise<GlyphBundle> {
  const library = await loadPrototypeLibrary(resolve(examplesDir, "prototype-library.json"));
  const records: Record<string, GlyphRecord> = {};
  const traces: Record<string, RuleTrace> = {};
  for (const ch of chars) {
    const rec = resolve(examplesDir, `glyph-record-${ch}.json`);
    const trc = resolve(examplesDir, `rule-trace-${ch}.json`);
    records[ch] = await loadGlyphRecord(rec);
    traces[ch] = await loadRuleTrace(trc);
  }
  return { library, records, traces };
}
