---
title: Authored decomposition layer + prototype graph — design
created: 2026-04-23
tags: [type/design, topic/chinese-font, topic/scene-graph, topic/prototype-graph]
source: self
status: active
related:
  - "[[glyph-scene-graph-spec]]"
  - "[[discussion-0003]]"
  - "[[discussion-0004]]"
  - "[[2026-04-22-mmh-metadata]]"
  - "[[2026-04-22-vector-component-composition]]"
  - "[[2026-04-22-ccfont]]"
  - "[[2026-04-22-sfgn-skeleton]]"
  - "[[2026-04-22-virtual-coordinates-only-design]]"
---

# Authored decomposition layer + prototype graph — design

Reactivates the day-one design that was deferred for shipping speed:
**MMH is one of several decomposition sources, not the oracle**, and
**the prototype library is a graph, not a per-glyph tree**. Geometry
remains measured affines in 1024² (the binding rule from
`.agent/skills/05-engine/glyph-geometry/SKILL.md` is unchanged).

## Why this plan now

The ceiling we hit at the end of v2 is not a measurement bug. It is a
data-source bug: 1462 of 4808 chars are non-verified, and the failure
modes (missing chars, wrong partition arity, missing components) are all
"MMH does not have what we need." Patching MMH-handling code further
has diminishing returns. The architecturally-correct fix — an authored
override layer + multi-source decomposition — is now also the
practically shortest path forward.

The same plan has been latent in the design since 2026-04-21:

> *"IDS provides the initial hierarchical scaffold; the glyph scene tree
> refines that scaffold into reusable atomic prototypes."*
> — `vault/references/discussion/discussion-0004.md`

> *"Glyph assembly is tree-based. Component reuse is graph-based."*
> — same.

Plan 09–13 built the geometry and bulk-extraction slice of that design.
The authoring layer and the graph were never wired. This plan finishes
that work.

## Two structural ideas, applied concretely

### Tree (per-glyph) — exists but un-authorable

`glyph.layout_tree` already encodes the per-symbol composition tree, and
the schema already has `RefinementMode` (`keep | refine | replace`),
`anchor_bindings`, `prototype_ref`, `transform`. **What is missing is a
file format and code path that lets a human override the tree for one
char.** Right now the tree comes from MMH's `matches`; if MMH is wrong
or absent, there is no escape hatch.

### Graph (cross-corpus) — partial

`prototype` (nodes) and two edges exist:

- `glyph -uses-> prototype` (with `instance_id`, `position`, `placed_bbox`).
- `prototype -variant_of-> prototype` (with `reason`).

Missing edges and attributes that turn the prototype library into a
useful graph:

| Element | Purpose | Source |
|---|---|---|
| `prototype -decomposes_into-> prototype` | abstract refinement at library level (e.g. `言 → 言_top, 言_bars, 言_stem, 言_box`) | authored, materialised from `data/glyph_decomp/` |
| `prototype -appears_in-> glyph` | materialised inverse of `uses` for fast prototype-browser lookup | trigger on `uses` upsert |
| `glyph -has_kangxi-> prototype` | Kangxi radical edge | MMH `radical` field |
| `prototype.role` | Dong-Chinese tag (meaning/sound/iconic/distinguishing/unknown) | authored, optional |
| `prototype.etymology` | (pictographic/ideographic/pictophonetic/null) | MMH `etymology` field on the *glyph*; copied to prototype when the prototype IS the whole glyph |
| `prototype.productive_count` | how many glyphs reuse this prototype (HanziCraft "productive components" metric) | computed from `uses` count |

These are exactly the affordances that let a future authoring agent
prioritise "what to author next" — start with the prototypes that most
glyphs depend on.

## Lessons lifted from external research

Filtered through the geometry skill: each idea below is either
**adopted** (drives a Plan 14 task), **noted** (validation only, no
code), or **explicitly rejected** (incompatible).

| Source | Idea | Disposition | Plan 14 task |
|---|---|---|---|
| `2026-04-22-mmh-metadata` | Use MMH `radical` and `etymology` (we already use `matches`) | Adopt | Task 5 |
| `2026-04-22-mmh-metadata` | Cross-check `decomposition` (IDS) against `cjk-decomp` | Adopt (peer source) | Task 2 |
| `2026-04-22-vector-component-composition` (arXiv 2404.06779) | 6-param affine matches our `transform` shape | Validation only | — |
| same | Centroid + inertia distances as standalone QA | Adopt | Task 10 |
| same | ~11K components ÷ 90K chars = ~1:8.2 ratio as a library-size bound | Note | (planning bound) |
| `2026-04-22-ccfont` | CJKradlib RadicalFinder as a *peer* decomp source | Note (defer to v3 if needed) | — |
| `2026-04-22-sfgn-skeleton` | 415 radicals over ~3,755 chars as another size bound | Note | (planning bound) |
| `2026-04-22-ahp-component-deformation` | AHP-derived weights over preset categories | **Reject** (D4 violation) | — |
| CCFont GAN composition / SFGN feature tensor | Image-domain composition | **Reject** (D4 violation) | — |
| Discussion 0001/0003 — HanziCraft "productive components" | Frequency-weighted reuse signal | Adopt | Task 6 |
| Discussion 0001 — Dong Chinese role coloring | meaning/sound/iconic/distinguishing/unknown | Adopt (schema only; sparse authoring) | Tasks 4 + 7 |
| Discussion 0003 — IDS as bootstrap, scene graph as backend | three decomposition layers (structural / refinement / instance), `keep|refine|replace` modes | Adopt | Tasks 1 + 3 |
| Discussion 0003 — Quadtree only as acceleration index, not authoring | (already follow this) | Validation only | — |
| Discussion 0004 — Constraint vocabulary (`align_y`, `attach`, `inside`, …) replaces categorical relations | Schema declared; runtime emission deferred | Defer (post-Plan-14) | — |

## Invariants (must hold after Plan 14)

1. **Geometry rule unchanged.** Every placement is a measured affine in
   1024². No preset bucket. No global slot weights. The guard test from
   Task 0 enforces this repo-wide and will catch any regrowth.
2. **MMH is a peer source, not the oracle.** All decomposition lookups
   go through `char_decomposition_lookup(char)` which tries
   `authored → animCJK → MMH → cjk-decomp` and returns the first hit.
   Geometry measurement still happens against the chosen partition.
3. **Authored layer is sparse and additive.** Empty by default. One
   `data/glyph_decomp/<char>.json` per char that needs human override.
   Authoring an override does not regenerate the 3331 already-verified
   records.
4. **Prototype graph is queryable, not just storable.** Every new edge
   and attribute has at least one inspector view that displays it.
5. **`RefinementMode` actually dispatches.** `keep` reuses the
   prototype as-is; `refine` recurses into children; `replace` swaps the
   prototype_ref for a variant. The schema field stops being decorative.
6. **Every new Plan-14 task produces a trace record.** See §Trace
   ledger below.

## Schema changes

### Authored decomposition file (`data/glyph_decomp/<char>.json`)

Sparse override — one file per char that needs hand-authoring. Pydantic
schema in `project/py/src/olik_font/sources/authored.py`; mirrored Zod
schema in `project/ts/packages/glyph-schema/src/authored-decomp.ts`.

```json
{
  "schema_version": "0.1",
  "char": "X",
  "supersedes": "mmh",
  "rationale": "MMH partition gives 3 components but the visual decomposition is 2 + nested 1.",
  "authored_by": "alice",
  "authored_at": "2026-04-23T10:14:00Z",
  "partition": [
    {
      "prototype_ref": "proto:u4eba",
      "mode": "keep",
      "source_stroke_indices": [0, 1]
    },
    {
      "prototype_ref": "proto:u53e3_in_X",
      "mode": "refine",
      "source_stroke_indices": [2, 3, 4],
      "children": [
        {"prototype_ref": "proto:dot", "mode": "keep", "source_stroke_indices": [2]},
        {"prototype_ref": "proto:hook", "mode": "keep", "source_stroke_indices": [3, 4]}
      ]
    }
  ]
}
```

`supersedes` records which automatic source this override displaces, for
later audit. `partition` is the per-char tree; geometry still measured
from the listed `source_stroke_indices`. `mode: replace` carries an
extra `replacement_proto_ref` field.

### SurrealDB schema additions

In `project/py/src/olik_font/sink/schema.py`:

```sql
DEFINE TABLE decomposes_into TYPE RELATION FROM prototype TO prototype SCHEMAFULL;
DEFINE FIELD ordinal ON decomposes_into TYPE int;        -- order within parent
DEFINE FIELD source ON decomposes_into TYPE string;      -- "authored" | "mmh" | "animcjk" | "cjk-decomp"
DEFINE INDEX decomposes_into_in_out ON decomposes_into FIELDS in, out UNIQUE;

DEFINE TABLE appears_in TYPE RELATION FROM prototype TO glyph SCHEMAFULL;
DEFINE FIELD instance_count ON appears_in TYPE int;      -- how many uses edges contribute
DEFINE INDEX appears_in_in_out ON appears_in FIELDS in, out UNIQUE;

DEFINE TABLE has_kangxi TYPE RELATION FROM glyph TO prototype SCHEMAFULL;
DEFINE INDEX has_kangxi_in ON has_kangxi FIELDS in UNIQUE;

DEFINE FIELD role ON prototype TYPE option<string>
       ASSERT $value IS NONE OR $value IN ["meaning","sound","iconic","distinguishing","unknown"];
DEFINE FIELD etymology ON prototype TYPE option<string>
       ASSERT $value IS NONE OR $value IN ["pictographic","ideographic","pictophonetic"];
DEFINE FIELD productive_count ON prototype TYPE int DEFAULT 0;

DEFINE FIELD etymology ON glyph TYPE option<string>
       ASSERT $value IS NONE OR $value IN ["pictographic","ideographic","pictophonetic"];
```

Migration is idempotent (`DEFINE … IF NOT EXISTS` patterned after
existing `ensure_schema`).

## Sources priority chain

```
char_decomposition_lookup(char) =
  load_authored(char)                     # data/glyph_decomp/<char>.json
  ?? load_animcjk(char)                   # already implemented; promoted to peer
  ?? load_mmh(char)                       # current oracle; demoted to fallback
  ?? load_cjk_decomp(char)                # last resort
  ?? raise NoDecompositionAvailable(char)
```

The function returns a `Decomposition` dataclass with:
- `partition: list[PartitionNode]` — per-component stroke index lists
- `source: Literal["authored", "animcjk", "mmh", "cjk-decomp"]` — provenance
- `confidence: float` — for sources that report it (animCJK does;
  authored is always 1.0; MMH and cjk-decomp default to 1.0 unless
  there's a known disagreement)

Geometry measurement (`measure_bbox_from_strokes`) runs against the
chosen partition. Compose still walks measured transforms.

## Inspector views (the user-facing surface)

### DecompositionExplorer (per-glyph tree)

Currently a naive row-by-depth flow. Upgraded to:

- **dagre tree layout** (top-down, child nodes flow down).
- **Mode coloring** matching the gallery convention: blue border for
  `measured` (leaves), amber for `refine` (internal), grey for `leaf`
  (no children, no measurement).
- **Mode badge** — visible chip showing `keep | refine | replace`.
- **Source badge** — chip showing which source emitted this partition
  (`authored` / `animcjk` / `mmh` / `cjk-decomp`).
- **AuthoringPanel** (Task 8) — when a node is selected, side panel
  shows *Keep* / *Refine into N children* / *Replace with prototype*
  buttons. *Save* writes `data/glyph_decomp/<char>.json`.

### PrototypeBrowser (per-prototype graph) — new view

- Pick a prototype.
- Force-directed graph centred on that prototype, showing:
  - `variant_of` parent + sibling variants
  - `decomposes_into` children
  - `appears_in` glyphs (top N by `productive_count`, expandable)
- Node attribute panel: `role`, `etymology`, `productive_count`.

This view is what makes the graph editable and what surfaces "author
this prototype next" priorities.

## QA additions

- **`prototypes/geom_stats.py`** — `centroid_distance(record)` and
  `inertia_spread(record)`. Standalone scalar metrics, computed at
  `build_glyph_record` time, written into `iou_report` alongside `mean`,
  `min`, `per_stroke`. Borrowed from the vector-component-composition
  paper's losses, used here as standalone QA, not as a training signal.
  Should correlate with IoU (Pearson r ≥ 0.5 over the 4808 corpus); if
  not, the metric is mis-implemented.

## Measurement and verification

Each Plan 14 task carries one or more **measurements** that another
agent can re-verify, plus a **trace record** appended to a ledger.

### Measurement types

- **Programmatic.** pytest counts, ruff/typecheck pass, SurrealDB row
  counts, Pearson correlation thresholds, idempotent-migration check.
- **Visual (kimi CLI).** Inspector views captured via Playwright, sent
  through the existing kimi-CLI pattern from `scripts/verdict_v2.py`:

  ```bash
  kimi --work-dir <out_dir> --print --yolo --final-message-only \
       -p "<verification prompt with strict JSON output schema>"
  ```

  Per the binding rule in
  `feedback_visual_verifier_model.md`: never silently substitute a
  smaller local vision model for kimi. If kimi is unreachable, the
  task's verdict is `BLOCKED: kimi unavailable`, not "passed".

### Trace ledger

`vault/references/plan-14-trace.md` is initialised by Task 0 and
appended by each subsequent task. One row per task:

```markdown
| task | commit | metric | value | kimi_verdict | timestamp |
|---|---|---|---|---|---|
| 0 | abc1234 | guard_violations | 0 | n/a | 2026-04-23T10:00:00Z |
| 7 | def5678 | dagre_renders + 4_seed_chars_tree_correct | true | pass (kimi:plan-14-kimi-verdicts/task-07.md) | 2026-04-23T11:42:00Z |
```

Per-task kimi verdict transcripts go to
`vault/references/plan-14-kimi-verdicts/task-NN-<slug>.md`. Each file
contains: prompt sent, raw kimi stdout, parsed JSON verdict, screenshot
path.

This combination — programmatic measurement + kimi visual + trace
ledger — gives downstream sessions and reviewers a way to re-verify
claims without re-running the workflow.

## End-to-end demo (the proof gate)

Task 11 is the gate. Pick one currently-failed char (`status =
failed_extraction`), author its decomposition through the inspector
authoring panel, save the file, run `olik extract retry --chars <c>`,
observe the char flip to `verified`. Kimi verdict on before/after
composed PNGs. **That round-trip is Plan 14's done definition.**

## Out of scope (defer to a later plan)

- Populating `constraints[]` per node (the constraint vocabulary is
  declared but not emitted at runtime).
- Per-prototype anchor declarations as a first-class library feature
  (anchors stay implicit until authoring tells us we need them).
- Learned layout adapter / CAR-style regressor (vector-component-composition
  bullet 4 — defer to v4+).
- CHISE IDS as a fourth source (postpone until authoring volume tells us
  the three current sources are insufficient).
- Bulk regeneration of the 3331 verified records (the authored layer is
  additive; existing verified records keep their MMH-measured form).
- Styling changes (ComfyUI bridge unchanged).
- Refine of the constraint solver (`align_y`, `attach`, etc. stay
  schema-only).

## Reference trail

- Spec foundation: `[[glyph-scene-graph-spec]]`,
  `[[2026-04-21-glyph-scene-graph-solution-design]]`.
- Discussion threads: `[[discussion-0003]]` (component-first pipeline,
  scene graph), `[[discussion-0004]]` (constraint scene graph, IDS as
  bootstrap, tree+graph duality, keep/refine/replace).
- Paper notes: `[[2026-04-22-mmh-metadata]]`,
  `[[2026-04-22-vector-component-composition]]`, `[[2026-04-22-ccfont]]`,
  `[[2026-04-22-sfgn-skeleton]]`, `[[2026-04-22-ahp-component-deformation]]`.
- Geometry rule: `.agent/skills/05-engine/glyph-geometry/SKILL.md`.
- Prior plan that deleted the preset vocabulary:
  `[[2026-04-22-virtual-coordinates-only-design]]` /
  `[[2026-04-22-11-virtual-coordinates-only]]`.
- Plan that this design realises: `[[2026-04-23-14-authored-decomp-and-prototype-graph]]`.
- Trace ledger: `vault/references/plan-14-trace.md`.
- Kimi verdict transcripts: `vault/references/plan-14-kimi-verdicts/`.
