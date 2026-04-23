---
title: Plan 14 — Authored decomposition layer + prototype graph
created: 2026-04-23
tags: [type/plan, topic/chinese-font, topic/scene-graph, topic/prototype-graph]
source: self
status: active
related:
  - "[[2026-04-23-authored-decomp-and-prototype-graph-design]]"
  - "[[glyph-scene-graph-spec]]"
  - "[[discussion-0003]]"
  - "[[discussion-0004]]"
---

# Plan 14 — Authored decomposition layer + prototype graph

Realises `[[2026-04-23-authored-decomp-and-prototype-graph-design]]` —
the day-one design that was deferred for shipping speed during
Plans 09–13. Adds an authored override layer for per-glyph
decomposition, demotes MMH to one of several peer sources, extends the
prototype graph with `decomposes_into`/`appears_in`/`has_kangxi`
edges, and adds the inspector views (DecompositionExplorer authoring
panel + new PrototypeBrowser) that make the graph visible and editable.

Geometry rule (`.agent/skills/05-engine/glyph-geometry/SKILL.md`)
remains binding — Task 0 enforces it repo-wide via a guard test.

Executed end-to-end via Archon workflow
`plan-14-authored-decomp-and-prototype-graph.yaml`. Each task carries a
**measurement** another agent can re-verify, and each task appends a
row to **`vault/references/plan-14-trace.md`** so the work can be
audited later. Visual measurements use **kimi CLI** following the
pattern from `scripts/verdict_v2.py`.

## Tasks

Each task ends with a commit whose message is normative. Some tasks
also append to the trace ledger and write a kimi verdict transcript;
those side-effects are part of the task definition, not optional.

### Task 0 — Repo-wide preset-vocabulary guard test

Make the cleanup we just did irreversible.

1. Add `project/py/tests/test_preset_vocabulary_guard.py`. Scans:
   - `project/py/src/`, `project/py/tests/`, `project/py/data/`,
   - `project/ts/packages/*/src/`, `project/ts/packages/*/test/`,
   - `project/ts/apps/*/src/`, `project/ts/apps/*/public/data/`,
   - `project/schema/examples/`.

   For literal substrings: `preset:`, `slot_bbox`, `slot_weight`,
   `_LEFT_RIGHT_WEIGHT`, `_TOP_BOTTOM_WEIGHT`, `_ENCLOSE_PADDING`,
   `_REPEAT_TRIANGLE_SCALE`. Plus the regex `\b(left_right|top_bottom|repeat_triangle)\b`
   (word-bounded so test function names with `_simple_two_components`
   don't false-match).

   Excludes: the guard file itself; `node_modules/`, `dist/`, `.venv/`,
   `__pycache__/`. Excludes `project/py/tests/test_extraction_plan_shape.py`
   (which contains `"preset:"` as an assertion target — already an
   intentional guard).

2. Initialise the trace ledger
   `vault/references/plan-14-trace.md` with the header row and append
   the Task 0 row.

3. **Measurement**: `pytest -k test_preset_vocabulary_guard -v` reports
   1 passed, 0 failed; the test scans ≥ 30 files and finds 0
   violations. The CI gate is the test itself.

4. **Trace**: `task=0, commit=<sha>, metric=guard_violations, value=0,
   kimi_verdict=n/a`.

5. Commit:
   `feat(test): repo-wide guard against preset vocabulary regrowth`.

### Task 1 — Authored decomposition layer schema + loader

1. Create `project/py/data/glyph_decomp/.gitkeep` (empty dir).
2. Add `project/py/src/olik_font/sources/authored.py`:
   - Pydantic models `AuthoredPartitionNode`, `AuthoredDecomposition`
     matching the schema in the design doc.
   - `load_authored(char: str, root: Path = DEFAULT_ROOT) -> AuthoredDecomposition | None`.
3. Mirror schema in
   `project/ts/packages/glyph-schema/src/authored-decomp.ts` (Zod).
4. Add a *sample* file for one currently-failed char (run
   `olik extract list --status failed_extraction --limit 1` to pick one).
   Hand-author its `partition` against the actual MMH stroke layout for
   that char. Store at `project/py/data/glyph_decomp/<char>.json`.
5. Tests:
   - `project/py/tests/test_authored_loader.py` — round-trips the sample;
     rejects malformed schema; returns None when no file exists.
   - `project/ts/packages/glyph-schema/test/authored-decomp.test.ts` —
     parses the sample file via Zod.

6. **Measurement**: pytest count for `test_authored_loader` = expected;
   the sample file validates against both schemas; `pnpm --filter
   @olik/glyph-schema test` passes.

7. **Trace**: append `task=1, commit=<sha>, metric=sample_char,
   value=<char>, kimi_verdict=n/a`.

8. Commit:
   `feat(py): authored decomposition layer (data/glyph_decomp loader)`.

### Task 2 — Unified char_decomposition_lookup with priority chain

1. In `project/py/src/olik_font/sources/unified.py`, add (or extend
   the existing `UnifiedLookup`):
   ```python
   def char_decomposition_lookup(self, char: str) -> Decomposition | None:
       return (
           load_authored_decomp(char)
           or self.animcjk.lookup(char)
           or self.mmh.lookup_partition(char)
           or self.cjk_decomp.lookup(char)
       )
   ```
   Returns a `Decomposition` dataclass with `partition`, `source`,
   `confidence`. Each branch wraps the source-specific shape into the
   common dataclass.

2. Replace every call site that hard-codes one source with this
   lookup. Concretely, audit:
   - `bulk/planner.py`
   - `decompose/instance.py`
   - `cli.py` `_build_artifacts` and `_cmd_db_sync`

3. Tests in `project/py/tests/test_unified_decomposition_lookup.py`:
   - Priority order: when authored exists, it wins over MMH for the
     same char; when only MMH exists, MMH wins; when none exist, returns
     None.
   - **Regression gate**: for the 4 seed chars (明 清 國 森),
     `compose_transforms` produces records whose `iou_mean ≥ 0.99`
     before AND after the refactor (compare against
     `project/ts/apps/inspector/public/data/glyph-record-<c>.json`).
   - **Authored-override gate**: writing a sample authored partition
     for 明 (e.g. swap order of children) and re-running the lookup
     yields a different partition; compose still runs without error.

4. **Measurement**: pytest count for `test_unified_decomposition_lookup`
   = expected; 4-seed IoU ≥ 0.99; authored override changes partition
   identity.

5. **Trace**: `task=2, commit=<sha>, metric=4seed_iou_min, value=<float>,
   kimi_verdict=n/a`.

6. Commit:
   `feat(py): unified decomposition lookup — authored → animCJK → MMH → cjk-decomp`.

### Task 3 — Compose dispatches on RefinementMode (keep | refine | replace)

1. Edit `project/py/src/olik_font/decompose/instance.py` and
   `project/py/src/olik_font/compose/walk.py`:
   - `keep`: behave as today (use prototype as-is at the measured
     transform).
   - `refine`: behave as today (recurse; parent transform = union of
     children's measured bboxes).
   - `replace`: read `replacement_proto_ref` from the partition node,
     swap `prototype_ref` for it, emit `input_adapter: "replaced"`.

2. Schema additions:
   - `RefinementMode` already declared in
     `project/ts/packages/glyph-schema/src/prototype.ts` — confirm
     `replace` is in the union.
   - `AuthoredPartitionNode.replacement_proto_ref: str | None` in
     `sources/authored.py`.

3. Tests `project/py/tests/test_compose_modes.py` — one test per mode:
   - `test_keep_uses_prototype_as_is`
   - `test_refine_recurses_into_children`
   - `test_replace_swaps_prototype_ref` (needs a sample authored file
     with a `replace` node + a fixture variant prototype)

4. **Measurement**: 3 new tests pass; no existing tests break.

5. **Trace**: `task=3, commit=<sha>,
   metric=mode_dispatch_tests_passed, value=3/3, kimi_verdict=n/a`.

6. Commit:
   `feat(py): compose dispatches on RefinementMode (keep|refine|replace)`.

### Task 4 — SurrealDB schema extensions

1. Edit `project/py/src/olik_font/sink/schema.py` to add:
   - `decomposes_into` RELATION (prototype → prototype, with `ordinal`,
     `source`, UNIQUE on (in,out))
   - `appears_in` RELATION (prototype → glyph, with `instance_count`,
     UNIQUE on (in,out))
   - `has_kangxi` RELATION (glyph → prototype, UNIQUE on `in`)
   - prototype fields: `role`, `etymology`, `productive_count`
   - glyph field: `etymology`
   - All `DEFINE … IF NOT EXISTS` for idempotency.

2. Add helpers in `project/py/src/olik_font/sink/surrealdb.py`:
   - `upsert_decomposes_into(db, parent_id, child_id, ordinal, source)`
   - `upsert_appears_in(db, proto_id, glyph_char, instance_count)`
   - `upsert_has_kangxi(db, glyph_char, kangxi_proto_id)`

3. Tests in `project/py/tests/test_sink_graph_schema.py`:
   - `ensure_schema` is idempotent (run twice; second call no-ops).
   - Each new RELATE round-trips one row.
   - Re-running upserts on the same in/out pair updates the payload, not
     duplicates the edge.

4. **Measurement**: pytest count for `test_sink_graph_schema` = 4+;
   `INFO FOR DB` (via a small helper test) lists all 3 new tables.

5. **Trace**: `task=4, commit=<sha>, metric=new_tables_in_schema,
   value=3, kimi_verdict=n/a`.

6. Commit:
   `feat(sink): prototype graph schema — decomposes_into, appears_in, has_kangxi`.

### Task 5 — MMH radical + etymology import → graph

1. Extend `project/py/src/olik_font/sources/makemeahanzi.py`:
   - `radical(char) -> str | None` — read MMH `dictionary.txt`'s
     `radical` field.
   - `etymology(char) -> Literal["pictographic","ideographic","pictophonetic"] | None`
     — parse from MMH `etymology.type`. Return `None` for chars that
     lack the field.

2. Wire into `cli.py` `_cmd_db_sync` and the bulk extract loop:
   - For each glyph synced, compute the kangxi prototype id (mint a
     new prototype `proto:kangxi_<radical_unicode>` if absent), then
     `upsert_has_kangxi(db, char, kangxi_id)`.
   - Set `glyph.etymology = mmh.etymology(char)`.

3. Tests in `project/py/tests/test_mmh_radical_etymology.py`:
   - `radical("明") == "日"` (or whatever MMH says).
   - `etymology("明")` matches MMH's reported value.
   - Sync 100 chars; ≥ 90 have `has_kangxi` populated; ≥ 60 have
     `etymology`. (Both thresholds are MMH-coverage-dependent; floor
     intentionally loose.)

4. **Measurement**: post-sync DB query: count of `has_kangxi` edges
   ≥ 90 over a 100-char sample; count of glyphs with non-null
   `etymology` ≥ 60.

5. **Trace**: append both counts.

6. Commit:
   `feat(sink): import MMH radical + etymology into prototype graph`.

### Task 6 — Productive count from `uses` edge

1. Add `compute_productive_counts(db) -> dict[str, int]` in
   `sink/surrealdb.py`. SurrealDB query:
   ```sql
   SELECT out AS proto_id, count() AS n
     FROM uses
     GROUP BY out;
   ```
   Then `UPDATE prototype SET productive_count = $n WHERE id = $proto_id`.

2. Expose as CLI `olik db recompute-counts` and call it at the end of
   `db sync` after upserts.

3. Tests in `project/py/tests/test_productive_counts.py`:
   - On a fresh ephemeral DB, insert 3 prototypes and 5 `uses` edges
     with known multiplicities; assert `compute_productive_counts`
     returns the expected per-prototype counts.

4. **Measurement (post-full-sync)**: dump top-10 productive prototypes
   to `vault/references/plan-14-productive-counts-2026-04-23.md`.
   Compare against HanziCraft's published top productive components
   (氵, 口, 人, 日, 月, 木, 心, 水, 火, 土). Acceptance: at least 6/10
   overlap. (Some divergence is expected — our extraction skews toward
   well-decomposed characters.)

5. **Trace**: `task=6, commit=<sha>,
   metric=top10_overlap_with_hanzicraft, value=<int>/10,
   kimi_verdict=n/a`.

6. Commit:
   `feat(sink): compute productive_count per prototype`.

### Task 7 — DecompositionExplorer upgrade (dagre + mode coloring)

1. Add `@dagrejs/dagre` dep to `project/ts/apps/inspector/package.json`.

2. Rewrite layout in
   `project/ts/apps/inspector/src/views/DecompositionExplorer.tsx`:
   - Use dagre top-down layout.
   - Color rules:
     - `input_adapter === "leaf"` → grey border `#64748b`
     - `input_adapter === "measured"` → blue border `#0ea5e9`
     - `input_adapter === "refine"` → amber border `#d97706`
     - `input_adapter === "replaced"` → purple border `#a855f7`
   - Mode badge (chip) showing `keep | refine | replace`.
   - Source badge (chip) showing partition source if present
     (`authored | animcjk | mmh | cjk-decomp`).

3. Vitest snapshot in
   `project/ts/apps/inspector/test/decomposition-explorer.test.tsx`
   for 森's tree shape.

4. **Visual measurement (kimi)**: a small Playwright script
   (`scripts/visual_verify_inspector.py`) launches `pnpm --filter
   @olik/inspector dev` against the public/data fixtures, navigates to
   each of 明 / 清 / 國 / 森, and screenshots the
   DecompositionExplorer view. Each screenshot is sent to kimi with a
   strict-JSON prompt:

   ```
   Look at the screenshot of an inspector tree view of the Chinese
   character {char}. Confirm: (1) it is a tree (parent at top, children
   below, edges connecting), (2) leaf nodes are coloured grey, internal
   nodes have blue or amber borders, (3) each node has a mode chip
   reading exactly one of "keep", "refine", or "replace". Output strict
   JSON one-line: {"char":"<c>","is_tree":bool,"colors_correct":bool,
   "mode_chips_present":bool,"verdict":"pass|fail"}.
   ```

   Pass = all three booleans true for all four screenshots.

5. **Trace**: `task=7, commit=<sha>,
   metric=kimi_pass_count_of_4, value=<int>,
   kimi_verdict=plan-14-kimi-verdicts/task-07-decomp-explorer.md`.

6. Commit:
   `feat(inspector): dagre tree + mode coloring in DecompositionExplorer`.

### Task 8 — DecompositionExplorer authoring panel

1. Add `project/ts/apps/inspector/src/views/AuthoringPanel.tsx`,
   shown when a node in the tree is selected.

2. Buttons:
   - **Keep** — sets selected node `mode = "keep"`.
   - **Refine into N** — splits node into N children at this level;
     opens prototype-picker for each child.
   - **Replace with…** — opens a prototype-picker; sets
     `mode = "replace"` and `replacement_proto_ref = <picked>`.
   - **Save** — emits `data/glyph_decomp/<char>.json` (downloads JSON
     in dev; in app-dev mode posts to a small local writer at
     `/api/authored-save`).

3. Add a tiny dev-only writer endpoint in inspector's vite plugin
   config or a sidecar script (`scripts/inspector_writer.py`) — only
   bound to `127.0.0.1`.

4. Tests:
   - vitest unit: clicking *Replace with X* updates the React state
     correctly and produces the expected JSON via the panel's
     `serialize()` helper.
   - manual e2e (recorded for trace): see Task 11.

5. **Measurement**: vitest passes; manual smoke — author-and-save flow
   produces a syntactically valid `glyph_decomp/<char>.json` file.

6. **Trace**: `task=8, commit=<sha>,
   metric=authored_file_validates, value=true, kimi_verdict=n/a`.

7. Commit:
   `feat(inspector): authoring panel writes data/glyph_decomp/<char>.json`.

### Task 9 — PrototypeBrowser inspector view

1. New view at
   `project/ts/apps/inspector/src/views/PrototypeBrowser.tsx`.

2. URL pattern: `/proto/<id>`. UI:
   - Force-directed reactflow centred on the chosen prototype.
   - Edges shown: `variant_of` (parent + siblings), `decomposes_into`
     (children).
   - Right-side panel: `appears_in` glyphs, sorted by `productive_count`
     descending, top 50 paginated.
   - Header attributes: `role`, `etymology`, `productive_count`.

3. Add `project/ts/packages/glyph-loader/src/proto-graph.ts` —
   loader that hits SurrealDB (or a static dump for dev) for the four
   queries this view needs.

4. Vitest snapshot for the rendered graph of one prototype.

5. **Visual measurement (kimi)**: Playwright navigates to `/proto/u6708`
   (月). Screenshot. Kimi prompt:

   ```
   Look at the screenshot of a prototype-browser view for the Chinese
   component 月. Confirm: (1) the central node label reads "月" or
   "u6708", (2) the right side panel lists glyph cells, (3) at least
   one of the listed glyphs is a character that visually contains 月
   (e.g. 明, 朋, 朝, 期). Output strict JSON one-line:
   {"central_correct":bool,"appears_in_listed":bool,
   "expected_glyphs_present":bool,"verdict":"pass|fail"}.
   ```

6. **Trace**: `task=9, commit=<sha>,
   metric=kimi_verdict, value=pass|fail,
   kimi_verdict=plan-14-kimi-verdicts/task-09-proto-browser.md`.

7. Commit:
   `feat(inspector): PrototypeBrowser view — prototype graph + productive_count`.

### Task 10 — Geom stats QA (centroid + inertia)

1. Add `project/py/src/olik_font/prototypes/geom_stats.py`:
   - `centroid_distance(record) -> float` — distance between the
     composed glyph's stroke centroid and its layout-tree-implied
     "expected" centroid.
   - `inertia_spread(record) -> float` — second moment of the stroke
     mass distribution.

2. Wire into `emit/record.py` `build_glyph_record`: add fields
   `iou_report.centroid_dist` and `iou_report.inertia_spread`.

3. Tests `project/py/tests/test_geom_stats.py`:
   - On 明's record: centroid roughly at (512, 512); inertia non-zero
     and finite.
   - Both metrics are pure functions (no side effects).

4. **Measurement (post-bulk-resync)**: compute Pearson correlation
   between `iou_mean` and `1 - centroid_dist/<scale>` over the 4808
   corpus. Acceptance: r ≥ 0.5. Also produce histograms saved to
   `vault/references/plan-14-geom-stats-2026-04-23.md`.

5. **Trace**: `task=10, commit=<sha>,
   metric=pearson_iou_vs_centroid, value=<float>,
   kimi_verdict=n/a`.

6. Commit:
   `feat(py): centroid + inertia spread QA metrics`.

### Task 11 — End-to-end demo (the proof gate)

1. Pick a `failed_extraction` char:
   ```bash
   .venv/bin/olik extract list --status failed_extraction --limit 1
   ```
   Record the char as `$DEMO_CHAR`.

2. Run the full author-and-fix flow:
   - `pnpm --filter @olik/inspector dev` (background)
   - Open `http://localhost:5176/glyph/$DEMO_CHAR`
   - Use the AuthoringPanel (Task 8) to create a partition for
     `$DEMO_CHAR`.
   - Save → file appears at
     `project/py/data/glyph_decomp/$DEMO_CHAR.json`.
   - `.venv/bin/olik extract retry --status failed_extraction --chars $DEMO_CHAR`.
   - Verify: `.venv/bin/olik extract report` shows verified count
     went from N to N+1.

3. **Measurements**:
   - Status flip: before = `failed_extraction`, after = `verified`.
   - IoU on the new record ≥ 0.90.
   - Kimi verdict on side-by-side composed PNG vs MMH reference (use
     `scripts/verdict_v2.py` pattern). Verdict must be `pass`.

4. **Trace** (3 rows for this task):
   - `task=11, commit=<sha>, metric=demo_char, value=$DEMO_CHAR, kimi_verdict=n/a`
   - `task=11, commit=<sha>, metric=status_flip, value=failed→verified, kimi_verdict=n/a`
   - `task=11, commit=<sha>, metric=composed_iou, value=<float>, kimi_verdict=plan-14-kimi-verdicts/task-11-e2e.md`

5. Commit:
   `test(e2e): authored decomposition flow — $DEMO_CHAR failed → verified`.

### Task 12 — Regression sweep + tag

1. Run all of:
   - `cd project/py && .venv/bin/pytest -q`
   - `cd project/ts && pnpm install && pnpm -r test && pnpm -r typecheck && pnpm -r --filter '!@olik/remotion-studio' build`
   - The Task 0 guard test (covered by pytest).
   - `.venv/bin/olik extract report` — verified count must be ≥ 3331
     (same as plan-13 baseline, plus the demo char from Task 11 = 3332).

2. Tag `git tag plan-14-authored-decomp-and-prototype-graph`.

3. Append final summary row to the trace ledger:
   `task=12, commit=<sha>, metric=verified_count, value=<int>, kimi_verdict=n/a`.

4. Output `COMPLETE`.

## Out of scope

- Populating `constraints[]` per node (declared but not emitted at runtime).
- Anchor declarations as a first-class library feature.
- Learned layout adapter (CAR-style regressor).
- CHISE IDS as a fourth source.
- Bulk regeneration of the 3331 verified records.
- Styling changes (ComfyUI bridge unchanged).
- Constraint solver (`align_y`, `attach`, etc. stay schema-only).

## Reference trail

- Design: `[[2026-04-23-authored-decomp-and-prototype-graph-design]]`.
- Spec foundation: `[[glyph-scene-graph-spec]]`.
- Trace ledger: `vault/references/plan-14-trace.md`.
- Kimi verdict transcripts: `vault/references/plan-14-kimi-verdicts/`.
- Workflow: `.archon/workflows/plan-14-authored-decomp-and-prototype-graph.yaml`.
