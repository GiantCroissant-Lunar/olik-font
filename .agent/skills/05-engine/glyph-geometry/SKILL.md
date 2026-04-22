---
name: glyph-geometry
description: Use whenever proposing, designing, or implementing anything that decides WHERE a Chinese character component sits inside a glyph — decomposition schemas, composition/compose code, extraction plans, slot logic, variant matching, or renderer math. Enforces the virtual-coordinate rule: component position is a measured transform in the 1024² virtual coordinate system, not a preset bucket (left_right / top_bottom / enclose / repeat_triangle) with a global weight.
category: 05-engine
layer: engine
related_skills:
  - "@vault-obsidian"
  - "@archon-workflows"
---

# Glyph geometry — the virtual-coordinate rule

This project is a **glyph scene graph** (see `vault/specs/glyph-scene-graph-spec.md` and `vault/specs/2026-04-21-glyph-scene-graph-solution-design.md`). Component placement is geometry, not a category.

## The rule (non-negotiable)

> **Each component instance carries a measured transform in the virtual 1024² coordinate system. Presets are a fallback authoring strategy for unmeasured cases, not the primary data model.**

What this means concretely:

- A component instance node stores `transform` (affine: prototype-local 1024² → glyph virtual 1024²) and/or `anchor_bindings`. Compose reads those directly.
- When we extract a prototype from an MMH source glyph, we **also measure** the bbox (and anchors) that instance occupied in the source, and record them on the instance.
- `left_right` / `top_bottom` / `enclose` / `repeat_triangle` are **labels on one authoring adapter**, not data. They must never be the only thing that tells compose where a component goes.

## What NOT to do

These patterns are the D4 violation — stop before writing them:

- `GlyphNodePlan.preset: "left_right"` as primary data with no transform → **forbidden**. Preset is at most metadata / debugging hint.
- `_LEFT_RIGHT_WEIGHT_L = 400.0 / 1024.0` as a global constant used for every `left_right` char → **forbidden**. Slot geometry is per-instance.
- "Let's add an `is_radical: bool` flag so the preset can pick a different weight" → **no**. Don't add categorical tags to keep the preset model alive. The categorical model is the bug.
- "Let's compute a per-char weight from stroke density at compose time, feed it to the same preset" → **still wrong**. Closer to right, but re-derives at compose time what should have been measured and stored at extraction time. Measure once, store, reuse.
- Treating compose as "pick a preset, stretch canonical bbox to slot bbox via `bbox_to_bbox_affine`" → that's non-uniform stretch + global slot. Both are geometry bugs.

## What TO do

- **Extraction writes geometry.** When `prototypes/extract_variant` carves 口 out of 囀, it records the measured source bbox and anchors of that instance. The variant row stores those, not just stroke indices.
- **Plans carry transforms.** `GlyphNodePlan` (or whatever the instance record is called) has `transform: Affine` and optionally `anchor_bindings: list[AnchorBinding]`. `preset` is `input_adapter` metadata only.
- **Compose reads, doesn't invent.** The compose algorithm from the spec: `if node.transform is set: use it; elif anchor_bindings: solve affine; else: error — under-specified.` No global weight tables.
- **Presets expand to transforms at authoring time, not compose time.** A preset adapter takes structural intent + measured child bboxes and emits `InstancePlacement` with a concrete transform. Once authored, the preset name is gone from the hot path.
- **Anchors are first-class.** Every prototype declares anchors; placement can refer to them symbolically (e.g. `inner.center → outer.center`).

## Canonical conventions

- Coordinate space: 1024 × 1024, origin top-left, MMH y-up (y=1024 is visual top pre-flip). The SVG y-flip lives in the renderer, not in compose.
- Transforms are affine (translate / scale / rotate / shear). Non-uniform scale is allowed when the measured source had non-uniform extent — but it's a consequence of measurement, not a default applied to a stretched canonical bbox.

## How to apply in practice

When you're about to write code, a spec, or a plan that involves placement:

1. Is the placement information **measured from a source glyph** (MMH reference, prior render) or **synthesised from a structural rule**? Measured is primary; synthesised is fallback.
2. Does the data model carry the **transform per instance**, or does compose reconstruct it from `(preset_name, global_params)`? If the latter, stop — you've reintroduced the D4 violation.
3. Does adding a feature require adding a new **preset-specific weight / anchor / rule**? That's a smell. Ask whether the missing info should live on the instance instead.
4. When reviewing someone else's design / plan / PR, search for `preset`, `weight_l`, `weight_top`, `slot_bbox`, `left_right`, `top_bottom` and check each usage against this skill.

## Reference trail

- `vault/specs/glyph-scene-graph-spec.md` — distilled spec; the source of D4.
- `vault/specs/2026-04-21-glyph-scene-graph-solution-design.md` — pass-1 solution; D4/D5 are in §Reviewable decisions.
- `vault/references/discussion/discussion-0003.md` / `discussion-0004.md` — raw threads where this was argued through.
- The Plan 10.1 revert (commit `7b9f8d8`) and the handover at `vault/handover/handover-2026-04-22-evening.md` — concrete evidence that preset-based placement cannot satisfy both radical and body components of the same layout family.
