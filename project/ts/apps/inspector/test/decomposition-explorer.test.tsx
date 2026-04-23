import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import type { GlyphRecord } from "@olik/glyph-schema";
import { describe, expect, test } from "vitest";
import { layoutTreeToFlow } from "../src/views/DecompositionExplorer.js";

const HERE = dirname(fileURLToPath(import.meta.url));
const FOREST_RECORD = JSON.parse(
  readFileSync(resolve(HERE, "../../../../schema/examples/glyph-record-森.json"), "utf-8"),
) as GlyphRecord;

describe("DecompositionExplorer", () => {
  test("lays out 森 as a dagre tree snapshot", () => {
    const flow = layoutTreeToFlow(FOREST_RECORD.layout_tree!, FOREST_RECORD.glyph_id);

    expect({
      nodes: flow.nodes.map(({ id, position, data }) => ({
        id,
        x: Math.round(position.x),
        y: Math.round(position.y),
        char: data.char,
        tone: data.tone,
        mode: data.wouldMode,
        sourceBadge: data.sourceBadge ?? null,
        components: [...data.components],
      })),
      edges: flow.edges.map(({ source, target }) => ({ source, target })),
    }).toMatchInlineSnapshot(`
      {
        "edges": [
          {
            "source": "inst:森_root",
            "target": "inst:tree_1",
          },
          {
            "source": "inst:森_root",
            "target": "inst:tree_2",
          },
          {
            "source": "inst:森_root",
            "target": "inst:tree_3",
          },
        ],
        "nodes": [
          {
            "char": "森",
            "components": [
              "tree",
              "tree",
              "tree",
            ],
            "id": "inst:森_root",
            "mode": "keep",
            "sourceBadge": null,
            "tone": "measured",
            "x": 268,
            "y": 24,
          },
          {
            "char": "tree",
            "components": [],
            "id": "inst:tree_1",
            "mode": "keep",
            "sourceBadge": null,
            "tone": "leaf",
            "x": 40,
            "y": 246,
          },
          {
            "char": "tree",
            "components": [],
            "id": "inst:tree_2",
            "mode": "keep",
            "sourceBadge": null,
            "tone": "leaf",
            "x": 268,
            "y": 246,
          },
          {
            "char": "tree",
            "components": [],
            "id": "inst:tree_3",
            "mode": "keep",
            "sourceBadge": null,
            "tone": "leaf",
            "x": 496,
            "y": 246,
          },
        ],
      }
    `);
  });
});
