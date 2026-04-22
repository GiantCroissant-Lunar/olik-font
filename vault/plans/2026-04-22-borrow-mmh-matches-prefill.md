---
title: Borrow — Auto-prefill source_stroke_indices from MMH `matches`
created: 2026-04-22
tags: [type/plan, topic/chinese-font, topic/scene-graph, topic/data-sources]
source: self
status: step-1-in-progress
related:
  - "[[2026-04-22-mmh-metadata]]"
  - "[[2026-04-22-11-virtual-coordinates-only]]"
  - "[[glyph-geometry]]"
---

# Borrow — Auto-prefill `source_stroke_indices` from MMH `matches`

## Source

Make Me a Hanzi, field `matches` in `dictionary.txt` — see [[2026-04-22-mmh-metadata]]. Already loaded into `MmhDictEntry.matches` by `project/py/src/olik_font/sources/makemeahanzi.py` (confirmed); just not yet threaded into the extraction-plan loader.

## The borrow (one sentence)

Use MMH's `matches` field (a per-stroke path down the decomposition tree) to auto-populate the `source_stroke_indices` field that Plan 11 Task 2 adds to `GlyphNodePlan`, replacing hand-authored integer lists in `extraction_plan.yaml`.

## Why this one

- **Compatible with the geometry skill.** `matches` is source-of-truth measurement data — exactly what `.agent/skills/05-engine/glyph-geometry/SKILL.md` wants us to feed extraction with. Nothing in this borrow reintroduces preset buckets.
- **Zero friction with Plan 11.** Plan 11 Task 2 *creates* `source_stroke_indices`. This borrow *fills* it. They compose cleanly; this borrow runs after Plan 11 lands without reopening anything.
- **Multiplies out to bulk extraction.** Plan 9.2 bulk-extraction becomes feasible only if `source_stroke_indices` can be produced without per-character human labour. `matches` is the mechanism.
- **Immediate starter is safe.** Step 1 below is a read-only demonstration script under `vault/plans/` — it touches no source tree and does not race with the Archon worktree.

## Concrete steps

### Step 1 — Demonstration script (DONE in this task) ✅

Write `vault/plans/2026-04-22-borrow-mmh-matches-prefill.py` that:

1. Reads the existing MMH cache at `project/py/data/mmh/{graphics,dictionary}.txt` (already fetched).
2. For each of the 4 seed characters (明 清 國 森), prints:
   - The character's IDS `decomposition` string.
   - The `matches` list (one entry per stroke, each a path down the decomp tree).
   - Derived `source_stroke_indices` per leaf component, obtained by grouping stroke indices by their `matches` path prefix.
3. Does NOT import from `olik_font.*` — the Archon worktree owns those files right now. The script has its own minimal JSONL loader.

Output of the script is what a future loader would produce; the script itself is the evidence the technique works on real data.

Commit message (Conventional-Commits-compliant, enforced by pre-commit):
```
feat(vault): add MMH `matches`-driven source_stroke_indices demo
```

### Step 2 — Post-Plan-11: Python adapter function

After Plan 11 lands on main:

1. Add `project/py/src/olik_font/sources/mmh_matches.py` with
   `def derive_source_stroke_indices(entry: MmhDictEntry) -> dict[tuple[int, ...], tuple[int, ...]]` — returns `{path → stroke_indices}`.
2. Unit tests against 明 / 清 / 國 / 森, comparing the derived indices to what the current hand-authored `extraction_plan.yaml` Task 5 will produce.

### Step 3 — Wire into extraction_plan loader

1. Extend `prototypes/extraction_plan.py`'s `load_extraction_plan` with an `auto_fill_from_mmh: bool = False` flag.
2. When true, any leaf `GlyphNodePlan` whose `source_stroke_indices` is `None` pulls the indices from the matcher by looking up the node's depth/position in the IDS tree and the corresponding `matches` path prefix.
3. Add a `--fill-from-mmh` flag to the CLI under `project/py/src/olik_font/cli.py`.

### Step 4 — Switch the shipped plan to derived indices

1. Regenerate `project/py/data/extraction_plan.yaml` via the CLI with the fill flag on.
2. Diff against the Task-5 hand-authored version; any divergence is a bug to file (either in our interpretation of `matches` or in the hand-authored plan).
3. Commit once they match bit-for-bit (or document the exception).

### Step 5 — Expand to bulk extraction

Apply the same fill to Plan 9.2's batch extractor so the bulk pipeline does not require hand-authored indices per glyph.

## Cost summary

- Step 1: ~1 hour (includes writing this doc). DONE.
- Steps 2–3: ~0.5 day.
- Step 4: ~0.25 day.
- Step 5: folds into Plan 9.2 rather than being separate.

## Prerequisite

Plan 11 lands on main. Until then, Steps 2–4 cannot proceed (they touch files the Archon worktree is editing). Step 1 does not share any write path with Plan 11 and is safe now.

## Out of scope for this borrow

- Neural-net-assisted decomposition. If `matches` is insufficient for some character, the fallback is still hand-authored YAML — not a learned regressor.
- Any preset-style layout inference. This borrow only provides `source_stroke_indices`; what compose does with them is pinned by Plan 11 Task 4 and the geometry skill.

## See also

- [[2026-04-22-mmh-metadata]] — the distilled note this borrow is drawn from.
- [[2026-04-22-11-virtual-coordinates-only]] — Plan 11, the prerequisite.
- [[glyph-scene-graph-spec]] §D2, §D9 — the decision points this borrow touches.
- `.agent/skills/05-engine/glyph-geometry/SKILL.md` — the rule this borrow satisfies rather than violates.
