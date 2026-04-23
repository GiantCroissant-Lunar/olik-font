declare module "@olik/glyph-loader" {
  import type {
    GlyphRecord,
    PrototypeGraphEdge,
    PrototypeGraphGlyphCell,
    PrototypeGraphNode,
    PrototypeGraphSnapshot,
    PrototypeLibrary,
    RuleTrace,
  } from "@olik/glyph-schema";

  export interface GlyphBundle {
    library: PrototypeLibrary;
    records: Record<string, GlyphRecord>;
    traces: Record<string, RuleTrace>;
  }

  export interface PrototypeBrowserData {
    focus: PrototypeGraphSnapshot["focus"];
    nodes: PrototypeGraphNode[];
    edges: PrototypeGraphEdge[];
    appearsIn: PrototypeGraphGlyphCell[];
  }

  export function loadGlyphRecordUrl(url: string): Promise<GlyphRecord>;
  export function loadPrototypeLibraryUrl(url: string): Promise<PrototypeLibrary>;
  export function loadPrototypeGraphUrl(url: string): Promise<PrototypeGraphSnapshot>;
  export function loadPrototypeBrowserDataUrl(url: string): Promise<PrototypeBrowserData>;
  export function loadRuleTraceUrl(url: string): Promise<RuleTrace>;
}
