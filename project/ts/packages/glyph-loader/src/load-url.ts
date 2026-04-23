import {
  GlyphRecord,
  PrototypeLibrary,
  RuleTrace,
  type GlyphRecord as GlyphRecordT,
  type PrototypeLibrary as PrototypeLibraryT,
  type RuleTrace as RuleTraceT,
} from "@olik/glyph-schema";

async function fetchJson(url: string | URL): Promise<unknown> {
  const resp = await fetch(url);
  if (!resp.ok) {
    throw new Error(`fetch ${url}: ${resp.status} ${resp.statusText}`);
  }
  return await resp.json();
}

export async function loadGlyphRecordUrl(url: string | URL): Promise<GlyphRecordT> {
  return GlyphRecord.parse(await fetchJson(url));
}

export async function loadPrototypeLibraryUrl(url: string | URL): Promise<PrototypeLibraryT> {
  return PrototypeLibrary.parse(await fetchJson(url));
}

export async function loadRuleTraceUrl(url: string | URL): Promise<RuleTraceT> {
  return RuleTrace.parse(await fetchJson(url));
}

export * from "./proto-graph.js";
