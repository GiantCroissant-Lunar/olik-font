---
title: Virtual coordinates only — design
created: 2026-04-22
tags: [type/design, topic/chinese-font, topic/scene-graph]
source: self
status: active
related:
  - "[[glyph-scene-graph-spec]]"
  - "[[2026-04-21-glyph-scene-graph-solution-design]]"
  - "[[handover-2026-04-22-evening]]"
---

# Virtual coordinates only — design

Non-negotiable corrective pass. Remove every use of the preset vocabulary
(`left_right`, `top_bottom`, `enclose`, `repeat_triangle`) and global slot-weight
constants from both code and data. Component placement is a **measured affine
transform in the 1024² virtual coordinate system**, per decision D4 of
`[[glyph-scene-graph-spec]]`. Presets are not data. Measurement is data.

## Context

- The committed scene-graph design (D4) said the data model has no preset
  enum — only `transform` + `anchor_bindings`. The implementation drifted
  into preset-as-primary-data + compose-time stretch to global slot bboxes.
- Plan 10.1 shipped an aspect-preserving slot fit and had to be reverted
  (commit `7b9f8d8`) because the preset model cannot satisfy both radical
  and body components of the same layout family.
- Plan 10.2 as previously framed (per-char weights from stroke density at
  compose time) is rejected. It keeps the preset machinery alive with a
  smarter weight function; the user has directed that this is still wrong.

## Invariants (must hold after this change)

1. **No preset identifier in the data model.** `GlyphNodePlan`,
   `GlyphPlan`, `InstancePlacement`, and all glyph-record JSON files use
   `transform` (prototype-local 1024² → glyph virtual 1024²) as the
   primary placement field. `input_adapter` on instances, if present at
   all, is free-form metadata like `"measured"`, `"refine"`, `"leaf"` —
   never `"preset:left_right"` / `"preset:top_bottom"` / `"preset:enclose"` /
   `"direct:repeat_triangle"`.
2. **Placement is measured, not synthesised.** Each instance node carries
   the MMH `source_stroke_indices` (per-instance, not per-prototype) of
   the strokes that instance occupies inside the parent glyph. At plan-load
   time, compose measures the union bbox of those strokes from MMH and
   emits a concrete affine transform. Canonical (0,0,1024,1024) → measured
   bbox via `geom.bbox_to_bbox_affine`.
3. **Compose walks and reads; it does not pick.** `compose/walk.py` dispatches
   on nothing. It reads `node.transform` directly. If a non-root node has
   no transform and no `source_stroke_indices`, it is an authoring error —
   raise `UnderspecifiedPlacement`.
4. **Presets, slot helpers, and weight constants are deleted code.**
   `constraints/presets.py` apply_* / slot_bbox / _slot_bbox_* / `_LEFT_RIGHT_WEIGHT_L` /
   `_TOP_BOTTOM_WEIGHT_TOP` / `_ENCLOSE_PADDING` / `_REPEAT_TRIANGLE_SCALE`
   all go.
5. **Variant matching measures.** `bulk/variant_match` replaces its
   `slot_bbox` lookups with direct measurement of the variant candidate's
   stroke bbox. No preset-aware logic remains.
6. **Instance multiplicity via explicit stroke index lists.** 森's three 木
   are three sibling instances, each carrying its own
   `source_stroke_indices` pointing at different strokes of 森. No
   `repeat_triangle` / `count` shorthand.

## Schema changes

### `PrototypePlan` (unchanged field set)

Prototypes keep `from_char` + `stroke_indices` to describe their canonical
geometry. Canonical bbox remains 0..1024² per prototype.

### `GlyphNodePlan` (additive + subtractive)

```python
@dataclass(frozen=True, slots=True)
class GlyphNodePlan:
    prototype_ref: str
    mode: Mode = "keep"                            # keep | refine | replace
    source_stroke_indices: tuple[int, ...] | None = None
    anchor_bindings: tuple[AnchorBinding, ...] = ()
    children: tuple[GlyphNodePlan, ...] = ()
    # NO `preset` field.
```

Semantics:
- `source_stroke_indices = None` means "use the prototype's own
  `stroke_indices` list". Valid only when the parent glyph char matches
  the prototype's `from_char` AND the indices are instance-accurate.
- Otherwise the instance provides its own list.

### `GlyphPlan` (subtractive)

```python
@dataclass(frozen=True, slots=True)
class GlyphPlan:
    children: tuple[GlyphNodePlan, ...] = ()
    # NO `preset`, `prototype_ref`, `count`.
```

A 森-style multi-instance glyph becomes three `children` entries with
explicit `source_stroke_indices`.

### `InstancePlacement` (unchanged shape, stricter contents)

Already has `transform: Affine | None` and `input_adapter: str | None`.
After this refactor, `input_adapter` is one of `"measured"` (filled from
`source_stroke_indices`), `"refine"` (carries children, placement is the
union of descendants), or `"leaf"`. Never a preset identifier.

### JSON glyph record (`project/schema/examples/*.json`)

Regenerated. Every `layout_tree` node carries a non-null `transform`.
`input_adapter` values change from `"preset:left_right"` etc. to
`"measured"` / `"refine"` / `"leaf"`. No other schema churn.

### `extraction_plan.yaml`

Rewritten. Each `glyphs.<char>.children` entry is:

```yaml
- prototype_ref: proto:sun
  mode: keep
  source_stroke_indices: [0, 1, 2, 3]
```

The `preset:` key is gone from every glyph and every nested node.

## Compose algorithm (replaces current `compose/walk.py`)

```
compose_transforms(node, parent_transform=Affine.identity, mmh):
  if node.transform is None:
    if node.source_stroke_indices is None:
      raise UnderspecifiedPlacement(node.id)
    bbox = measure_bbox(mmh[parent_char].strokes, node.source_stroke_indices)
    node.transform = bbox_to_bbox_affine(CANONICAL, bbox)
  for child in node.children:
    recurse with parent_char = parent_char  # same root char
  return node with all transforms filled in
```

Refine-mode nodes: the parent's transform is the union bbox of its
children's measured bboxes; alternatively, the parent carries its own
`source_stroke_indices` covering the union. Pass-1 takes the union of
children route; authoring can override by setting parent indices
explicitly.

## Variant matching

`bulk/variant_match.py` currently calls
`constraints.presets.slot_bbox(preset, n, idx, glyph_bbox)` to predict
where a candidate variant's strokes should fall. After this refactor it:

1. Loads the candidate glyph's MMH paths.
2. For each prototype slot in the plan, measures the stroke bbox of the
   candidate indices that were matched to that slot.
3. Compares measured bbox to the prototype's canonical to score aspect /
   location fit. No preset vocabulary appears.

## Test churn

- Deleted: `test_preset_left_right.py`, `test_preset_top_bottom.py`,
  `test_preset_enclose.py`, `test_preset_repeat_triangle.py`.
- Rewritten: `test_compose_walk.py` around measured transforms.
- Added: `test_measure.py` (stroke-list bbox measurement, in-glyph
  placement for all four seed chars), `test_extraction_plan_shape.py`
  (YAML no longer has any `preset:` key anywhere).

## Visual acceptance

`apps/inspector/` reads the regenerated glyph records and renders both
the **Decomposition Explorer** (react-flow tree) and the **Placement
Debugger** (react-flow placement graph with transform/bbox per node).
Acceptance: screenshots of both views for 明, 清, 國, 森 are approved by
Gemma 4 (or the best available vision model) against the following
checks:

- Decomposition tree matches the IDS-like structural decomposition (明 =
  two leaves; 清 = left leaf + one refined subtree with two leaves; 國 =
  refine enclose → two children; 森 = three tree leaves as siblings).
- Placement graph shows each instance's bbox matching the MMH-source
  proportions — in particular, 明's 日 is a square-ish block in the
  upper-left area, not a stretched full-height column.
- No node in the placement view shows `input_adapter = preset:*`.

## Deferred (explicitly out of scope here)

- Anchor inference from geometry (anchors remain hand-declared in the
  prototype library).
- Learned layout adapter (future D-path).
- `replace` mode (schema-only already; stays that way).
- Iterative constraint solver.
