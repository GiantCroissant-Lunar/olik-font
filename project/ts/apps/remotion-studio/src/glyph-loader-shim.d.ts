declare module "@olik/glyph-loader" {
  import type { GlyphRecord, PrototypeLibrary, RuleTrace } from "@olik/glyph-schema";

  export interface GlyphBundle {
    library: PrototypeLibrary;
    records: Record<string, GlyphRecord>;
    traces: Record<string, RuleTrace>;
  }
}
