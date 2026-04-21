import { readFile } from "node:fs/promises";
import {
  GlyphRecord,
  PrototypeLibrary,
  RuleTrace,
  type GlyphRecord as GlyphRecordT,
  type PrototypeLibrary as PrototypeLibraryT,
  type RuleTrace as RuleTraceT,
} from "@olik/glyph-schema";

export async function loadGlyphRecord(path: string): Promise<GlyphRecordT> {
  const raw = await readFile(path, "utf-8");
  const parsed = JSON.parse(raw);
  return GlyphRecord.parse(parsed);
}

export async function loadPrototypeLibrary(path: string): Promise<PrototypeLibraryT> {
  const raw = await readFile(path, "utf-8");
  const parsed = JSON.parse(raw);
  return PrototypeLibrary.parse(parsed);
}

export async function loadRuleTrace(path: string): Promise<RuleTraceT> {
  const raw = await readFile(path, "utf-8");
  const parsed = JSON.parse(raw);
  return RuleTrace.parse(parsed);
}
