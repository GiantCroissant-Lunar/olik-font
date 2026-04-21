declare module "@olik/glyph-loader" {
  import type { GlyphRecord, PrototypeLibrary, RuleTrace } from "@olik/glyph-schema";

  export interface GlyphBundle {
    library: PrototypeLibrary;
    records: Record<string, GlyphRecord>;
    traces: Record<string, RuleTrace>;
  }

  export function loadGlyphRecordUrl(url: string): Promise<GlyphRecord>;
  export function loadPrototypeLibraryUrl(url: string): Promise<PrototypeLibrary>;
  export function loadRuleTraceUrl(url: string): Promise<RuleTrace>;
}
