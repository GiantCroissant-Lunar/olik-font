---
title: Plan 11 — Virtual coordinates only
created: 2026-04-22
tags: [type/plan, topic/chinese-font, topic/scene-graph]
source: self
status: active
related:
  - "[[2026-04-22-virtual-coordinates-only-design]]"
  - "[[glyph-scene-graph-spec]]"
---

# Plan 11 — Virtual coordinates only

Deletes the preset vocabulary from code and data. Replaces preset-driven
compose with measured transforms from MMH source strokes, as required by
decision D4 of the glyph scene graph spec. Executed end-to-end via Archon
workflow `plan-11-virtual-coordinates-only.yaml`; visual verification
with Gemma 4 happens after the workflow completes (not inside the loop).

Spec: `[[2026-04-22-virtual-coordinates-only-design]]`.

## Tasks

### Task 1 — Delete preset code

Remove preset-specific logic from the compose path.

1. Delete `project/py/src/olik_font/constraints/presets.py` in its entirety.
2. Delete:
   - `project/py/tests/test_preset_left_right.py`
   - `project/py/tests/test_preset_top_bottom.py`
   - `project/py/tests/test_preset_enclose.py`
   - `project/py/tests/test_preset_repeat_triangle.py`
3. `git commit -m "feat(py): drop preset adapters, slot helpers, and per-preset tests"`

### Task 2 — Schema refactor (GlyphNodePlan / GlyphPlan)

Remove the preset vocabulary from the plan dataclasses.

1. Edit `project/py/src/olik_font/prototypes/extraction_plan.py`:
   - Delete the `Preset` Literal.
   - Remove `preset: Preset | None` from `GlyphNodePlan`.
   - Remove `preset`, `prototype_ref`, `count` from `GlyphPlan`.
   - Add `source_stroke_indices: tuple[int, ...] | None = None` to
     `GlyphNodePlan`.
   - Update `_parse_node` and `load_extraction_plan` accordingly.
2. Add `project/py/tests/test_extraction_plan_shape.py`: fails if any
   parsed `GlyphPlan` or `GlyphNodePlan` has a `preset` attribute, and
   fails if the shipped `data/extraction_plan.yaml` contains the string
   `preset:` anywhere.
3. Commit: `feat(py): instance source_stroke_indices; drop preset from plan shape`.

### Task 3 — Measurement helper

Add the primitive that turns stroke indices into a measured affine.

1. Add `project/py/src/olik_font/prototypes/measure.py`:
   - `def measure_bbox_from_strokes(paths: Sequence[str]) -> BBox`
     (wraps `geom.bbox_of_paths`).
   - `def measure_instance_transform(mmh_paths_at_indices: Sequence[str], canonical: BBox = CANONICAL) -> Affine`
     (measures bbox, then `bbox_to_bbox_affine(canonical, bbox)`).
2. Add `project/py/tests/test_measure.py`:
   - For 明's strokes [0,1,2,3], the measured bbox is NOT (0,0,1024,1024)
     and NOT a stretched full-height column. Its width / height ratio is
     within [0.5, 1.6] (roughly square).
   - For 明's strokes [4,5,6,7], bbox is positioned to the right of 日's
     bbox and has a tall aspect (height > width).
3. Commit: `feat(py): measure per-instance transforms from MMH source strokes`.

### Task 4 — Compose rewrite

Replace `compose/walk.py` with a transform-reader.

1. Rewrite `project/py/src/olik_font/compose/walk.py`:
   - Signature stays `compose_transforms(node, glyph_bbox) -> (node, constraints)`.
   - No more `apply_*` calls. Remove all imports from
     `olik_font.constraints.presets`.
   - For each non-root node:
     - If `node.transform` is already set, keep it.
     - Else if the owning `InstancePlacement` carries
       `source_stroke_indices`, measure from MMH (inject MMH adapter
       via a small protocol object or module-level lookup keyed on the
       root glyph's char).
     - Else raise `UnderspecifiedPlacement(node.id)`.
   - Constraints returned by the walker is `()` in pass-1 (real
     constraint resolution is deferred). Remove resolved-primitive
     emission for presets.
2. Replace `test_compose_walk.py` with measurement-based tests:
   - Build a `GlyphPlan` for 明 with explicit `source_stroke_indices` on
     each child; call `compose_transforms`; assert the two children get
     non-identical, non-stretched transforms that place them side-by-side
     in the upper band of the 1024² space.
3. Commit: `refactor(py): compose walks measured transforms; no preset dispatch`.

### Task 5 — Rewrite `extraction_plan.yaml`

Port the 4 seed glyphs to instance-level `source_stroke_indices`.

1. Edit `project/py/data/extraction_plan.yaml`:
   - Remove every `preset:` key.
   - For each glyph entry, list instances with `prototype_ref`, `mode`,
     `source_stroke_indices`. For nested refine (e.g. 清 → 青), list the
     parent node with `mode: refine` and its own child instances; the
     parent's transform is derived as the union of its children's
     measured bboxes.
   - 森 becomes three sibling children with stroke indices
     `[0,1,2,3]`, `[4,5,6,7]`, `[8,9,10,11]` (confirm against MMH —
     adjust if the actual stroke count differs).
2. Commit: `data: extraction_plan.yaml uses explicit source_stroke_indices`.

### Task 6 — bulk / variant_match

Remove preset vocabulary from the variant-matching pipeline.

1. Edit `project/py/src/olik_font/bulk/variant_match.py`,
   `bulk/planner.py`, `bulk/reuse.py`, `bulk/batch.py`, `bulk/ops.py`:
   - Drop all imports of `olik_font.constraints.presets`.
   - Drop every call to `slot_bbox` / `apply_*`.
   - Replace slot-bbox predictions with direct measurement of the
     candidate variant's matched stroke indices, using the new
     `measure_bbox_from_strokes`.
   - Any preset string (`left_right` / `top_bottom` / …) embedded as
     a config field becomes either removed or renamed to a structural
     descriptor (e.g. `n_children: 2`). No preset name remains.
2. Edit `project/py/src/olik_font/rules/rules.yaml` to remove any
   preset-named rules; keep only structural/compose rules that survive
   the refactor.
3. Edit `project/py/src/olik_font/decompose/instance.py` to stop emitting
   `input_adapter: preset:*`. Emit `"measured"` for leaves with stroke
   indices, `"refine"` for nodes with children, `"leaf"` otherwise.
4. Update/add tests in `project/py/tests/` to cover the new flow. Any
   existing bulk test that asserts preset strings should now assert
   absence of preset strings.
5. Commit: `refactor(py): variant matching and bulk pipeline use measured bboxes`.

### Task 7 — Regenerate seed records and inspector fixtures

1. From `project/py`:
   ```bash
   .venv/bin/olik build 明 清 國 森 -o ../schema/examples/
   ```
   If the CLI subcommand is named differently, run the documented
   build command for the 4 seed chars.
2. Copy regenerated records into the inspector:
   ```bash
   cp project/schema/examples/*.json project/ts/apps/inspector/public/data/
   ```
3. Commit: `data: regenerate seed glyph records with measured transforms`.

### Task 8 — Regression sweep + tag

1. From `project/py`: `.venv/bin/pytest -q`. All tests green, no
   deprecation warnings involving `preset`.
2. From `project/ts`: `pnpm install && pnpm -r test && pnpm -r typecheck && pnpm -r --filter '!@olik/remotion-studio' build`.
3. `git tag plan-11-virtual-coordinates-only`.
4. Output `COMPLETE`.

## Out of scope

- Anchor inference from geometry.
- Learned layout adapter.
- Iterative constraint solver.
- Admin UI changes beyond whatever the regenerated records naturally
  cause (no admin-review UI refactor here; the admin UI reads
  `input_adapter` as a display string).
- Visual verification itself — handled after the workflow by the
  session operator using Gemma 4.
