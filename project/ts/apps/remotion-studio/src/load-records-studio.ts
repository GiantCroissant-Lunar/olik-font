import { staticFile } from "remotion";
import {
  GlyphRecord as GlyphRecordSchema,
  PrototypeLibrary as PrototypeLibrarySchema,
  type GlyphRecord,
} from "@olik/glyph-schema";
import type { GlyphBundle } from "@olik/glyph-loader";

export const SEED_CHARS = ["明", "清", "國", "森"] as const;

async function fetchJson(url: string): Promise<unknown> {
  const resp = await fetch(url);
  if (!resp.ok) {
    throw new Error(`fetch ${url}: ${resp.status} ${resp.statusText}`);
  }
  return await resp.json();
}

// Browser-side bundle loader used by Remotion Studio previews and
// rendered output. Reads the fixtures from the app's `public/data/` dir
// via Remotion's `staticFile()` helper. We don't import `@olik/glyph-loader`'s
// fs-backed `loadBundleFs` here because Remotion's webpack bundler
// cannot handle the transitive `node:fs/promises` import in a browser
// target.
export async function loadStudioBundle(): Promise<GlyphBundle> {
  const library = PrototypeLibrarySchema.parse(
    await fetchJson(staticFile("/data/prototype-library.json")),
  );
  const records: Record<string, GlyphRecord> = {};
  for (const ch of SEED_CHARS) {
    records[ch] = GlyphRecordSchema.parse(
      await fetchJson(staticFile(`/data/glyph-record-${ch}.json`)),
    );
  }
  return { library, records, traces: {} };
}
