import {
  PrototypeGraphSnapshot,
  type PrototypeGraphEdge,
  type PrototypeGraphGlyphCell,
  type PrototypeGraphNode,
  type PrototypeGraphSnapshot as PrototypeGraphSnapshotT,
} from "@olik/glyph-schema";

async function fetchJson(url: string | URL): Promise<unknown> {
  const resp = await fetch(url);
  if (!resp.ok) {
    throw new Error(`fetch ${url}: ${resp.status} ${resp.statusText}`);
  }
  return await resp.json();
}

export interface PrototypeBrowserData {
  focus: PrototypeGraphSnapshotT["focus"];
  nodes: PrototypeGraphNode[];
  edges: PrototypeGraphEdge[];
  appearsIn: PrototypeGraphGlyphCell[];
}

export async function loadPrototypeGraphUrl(
  url: string | URL,
): Promise<PrototypeGraphSnapshotT> {
  return PrototypeGraphSnapshot.parse(await fetchJson(url));
}

export async function loadPrototypeBrowserDataUrl(
  url: string | URL,
): Promise<PrototypeBrowserData> {
  const snapshot = await loadPrototypeGraphUrl(url);
  return {
    focus: snapshot.focus,
    nodes: snapshot.nodes,
    edges: snapshot.edges,
    appearsIn: snapshot.appears_in,
  };
}
