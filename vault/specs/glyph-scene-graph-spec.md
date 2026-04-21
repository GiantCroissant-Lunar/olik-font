---
title: Glyph Scene Graph — distilled spec
created: 2026-04-21
tags: [topic/chinese-font, topic/scene-graph, topic/spec, type/distilled]
source: self
distilled-from:
  - "[[discussion-0003]]"
  - "[[discussion-0004]]"
status: draft
---

# Glyph Scene Graph — distilled spec

A clean restatement of the design that emerged from the discussion chain. The raw threads are in [[index|the discussion MOC]]; this note is the usable output.

## One-line summary

> A glyph is a hierarchical composition tree of reusable prototypes, where each node may be refined, replaced, transformed, and styled — with a constraint-based scene graph as the backend and IDS decomposition as one possible frontend.

## Why this shape

- **Character-level generation doesn't scale** to 10,000+ CJK glyphs. Component-level generation + explicit layout does.
- **IDS relations (left_right, top_bottom, enclose, …) are too narrow** — fine as legacy tags for real CJK, but restrictive for invented logographic symbols.
- **Reconstruction and styling are separate concerns.** Reconstruction is deterministic geometry. Styling (brush, ink bleed, edge noise, aging) is graph-based image processing. Keep ComfyUI only in the styling stage.

## Three separating invariants

1. **Structure is hierarchical** — tree for assembly; graph/DAG for the shared prototype library.
2. **Geometry lives in a normalized virtual coordinate system** — 1024×1024 matches the Make Me a Hanzi stroke data convention.
3. **Styling is a separate transform**, not part of reconstruction.

## Node model

Replace categorical relation enums with a general node + constraint model.

```json
{
  "id": "node_12",
  "kind": "component",           // group | component | stroke | contour | mask | guide | attachment
  "parent": "group_3",
  "geometry_ref": "comp_water_variant_b",
  "transform": {
    "translate": [312, 188],
    "scale":     [0.62, 0.84],
    "rotate":    -0.08,
    "shear":     [0.03, 0.0]
  },
  "anchors": {
    "entry":  [0.1, 0.5],
    "exit":   [0.92, 0.47],
    "top":    [0.5, 0.0],
    "bottom": [0.5, 1.0]
  },
  "constraints": [
    {"kind": "inside",        "target": "frame_main"},
    {"kind": "avoid_overlap", "target": "node_13", "padding": 12},
    {"kind": "attach",        "from": "exit", "to": "node_13.entry"}
  ],
  "style_slots": {
    "stroke_family": "ink_brush_02",
    "texture_zone":  "edge_rough"
  }
}
```

## Constraint vocabulary

Primitives (composable):

- `align_x`, `align_y`
- `attach` (anchor → anchor)
- `inside` / `contain`
- `avoid_overlap`
- `preserve_gap`
- `tangent`
- `center_on_path`
- `radial_array`
- `mirror`
- `repeat`
- `distribute_along_curve`
- `order_x`, `order_y`, `stack_by_priority`

Classical IDS relations become **presets** that expand to constraint combinations, not primitives:

```json
{
  "preset": "left_right",
  "expands_to": [
    {"kind": "align_y",         "targets": ["A.center", "B.center"]},
    {"kind": "order_x",         "before": "A", "after": "B"},
    {"kind": "anchor_distance", "from": "A.right_mid", "to": "B.left_mid", "value": 20}
  ]
}
```

## Three decomposition layers

1. **Structural tree** — IDS-like coarse parse (compatible with HanziCraft / Make Me a Hanzi).
2. **Component refinement tree** — each structural node may decompose further or be replaced by a style-specific variant. This is where storage compression lives.
3. **Instance tree** — the actual build tree for one rendered symbol, referencing prototype IDs + transforms + styles.

Each node supports three modes:

- **keep** — use as-is
- **refine** — expand into child nodes
- **replace** — swap for an equivalent or style-specific variant

A component is **not** atomic in a universal sense — atomicity depends on the operation (layout / styling / export).

## Top-level glyph record

```json
{
  "glyph_id": "漢",
  "unicode":  "U+6F22",
  "coord_space": {
    "type":   "virtual",
    "width":  1024,
    "height": 1024,
    "origin": "top-left",
    "y_axis": "down"
  },
  "layout_tree":         {},
  "component_instances": [],
  "stroke_instances":    [],
  "render_layers":       [],
  "constraints":         [],
  "metadata":            {}
}
```

Minimum required fields for a first working spec: `glyph_id`, `coord_space`, `layout_tree`, `component_instances`, `stroke_instances`, `render_layers`, `style_slots`. Everything else is extension.

## Render layers (z-depth)

Z-depth lives in rendering, not in logical decomposition:

| z range | layer              |
|---------|--------------------|
| 0–9     | skeleton / guides  |
| 10–49   | stroke_body        |
| 50–69   | stroke_edge        |
| 70–89   | texture_overlay    |
| 90–99   | damage / shadow / emboss |

For printed styles, keep shallow (body / edge / texture). For handwritten/cursive, z-depth matters more because stroke crossings and ink pooling are part of the look.

## Where quadtree fits

**Not** as the authoring structure. Use for acceleration only:

- hit testing
- overlap detection
- local repainting
- nearest-neighbor stroke lookup
- texture tiling

> scene graph = semantic + geometric truth; quadtree = index

## Pipeline split

**Outside ComfyUI (deterministic):**

1. Parse text → character list
2. Decompose each character → IDS / refinement tree
3. Assign normalized layout boxes
4. Instantiate component/stroke prototypes
5. Apply transforms + constraints → composed glyph geometry
6. Optionally export SVG masks / depth maps / control maps

**Inside ComfyUI (styling):**

- Style transfer on components or strokes
- Brush simulation, edge roughening
- Ink bleed / erosion / carving / printing defects
- Consistency refinement / raster finishing

## Pending / open questions

- Raster-first vs. vector-first at the style stage. For a real font product, vector-first is leaning favorite.
- Exact schema for `constraints[]` — start with the primitive set above, extend as needed.
- Prototype library format — single graph/DAG or per-family files.
- Example end-to-end: pick one character (漢 or 語) and walk it through the pipeline to stress-test the schema.

## Diagram

Pipeline overview (stub — open in Obsidian with the Excalidraw plugin to expand):

![[glyph-scene-graph-pipeline.excalidraw]]

## See also

- Upstream data sources in the [[index|MOC's key references list]].
- [[discussion-0003]] for the full JSON schema draft.
- [[discussion-0004]] for the constraint / IDS-bootstrap argument.
- [[glyph-scene-graph-pipeline.excalidraw|Pipeline diagram source]]
