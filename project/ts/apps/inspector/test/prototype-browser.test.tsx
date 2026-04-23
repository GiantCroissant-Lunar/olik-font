import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import type { PrototypeGraphSnapshot } from "@olik/glyph-schema";
import { describe, expect, test } from "vitest";
import { buildPrototypeFlow } from "../src/views/PrototypeBrowser.js";

const HERE = dirname(fileURLToPath(import.meta.url));
const MOON_GRAPH = JSON.parse(
  readFileSync(resolve(HERE, "../../../../schema/examples/proto-graph-u6708.json"), "utf-8"),
) as PrototypeGraphSnapshot;

describe("PrototypeBrowser", () => {
  test("lays out 月 graph snapshot", () => {
    const flow = buildPrototypeFlow({
      focus: MOON_GRAPH.focus,
      nodes: MOON_GRAPH.nodes,
      edges: MOON_GRAPH.edges,
      appearsIn: MOON_GRAPH.appears_in,
    });

    expect({
      nodes: flow.nodes.map(({ id, data, position }) => ({
        id,
        label: data.label,
        kind: data.kind,
        x: Math.round(position.x),
        y: Math.round(position.y),
      })),
      edges: flow.edges.map(({ source, target, label }) => ({ source, target, label })),
    }).toMatchSnapshot();
  });
});
