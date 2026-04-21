---
title: "Plan 08 — SurrealDB foundation (design)"
created: 2026-04-21
tags: [type/spec, topic/scene-graph, topic/surrealdb]
status: draft
supersedes: null
relates-to:
  - "[[2026-04-21-glyph-scene-graph-solution-design]]"
  - "[[2026-04-21-03-python-compose-cli]]"
  - "[[2026-04-21-07-xyflow-inspector]]"
---

# Plan 08 — SurrealDB foundation (design)

## 1. Context & motivation

Passes 1–6 shipped a JSON-file-per-glyph pipeline: `olik build <chars>` emits
`project/schema/examples/glyph-record-<char>.json` plus `prototype-library.json`
and `rules.json`, and the inspector / Remotion / quickview apps read those files
over HTTP. That works at 4 characters. It does not work at the target scale:

- The project intends to grow to ~5000 chars (教育部常用字 4808). A 5000-file
  dataset is ~75 MB of JSON; shipping it to the browser in one go is a
  non-starter.
- Cross-glyph queries ("which characters use `proto:moon`?", "list glyphs with
  stroke count between 8 and 12", "order by IoU ascending to surface
  extraction failures") are expensive to compute over flat files and duplicate
  effort between Python and TS consumers.
- Plan 11 will introduce ComfyUI-generated style variants. Those need a
  concurrent writer (the ComfyUI job runner) and a concurrent reader (the
  admin UI watching for new results via LIVE queries). Static files cannot
  model that.

Plan 08 replaces static JSON as the source of truth with a SurrealDB instance.
It is the foundation that Plans 09 (bulk extraction), 10 (admin UI), and 11
(ComfyUI) all build on.

## 2. Goals

- Single source of truth for glyph + prototype + rule data, queryable from
  both Python (the extraction pipeline) and TypeScript (the apps).
- Schema that supports cross-glyph graph queries ("chars using proto X",
  "chars by radical") **and** efficient per-glyph detail retrieval for the
  admin UI detail drawer.
- Idempotent ingest: re-running `olik db sync 明 清 ...` produces no duplicate
  rows, no orphaned edges.
- Local-dev only: one SurrealDB process on `127.0.0.1:6480`, persistent via
  `surrealkv`. Auth is root/root (local-only trust model). Remote deployment
  and real auth are out of scope for Plan 08.
- Leaves the existing `olik build` JSON emitter intact so Plan 03's Archon
  workflows, the current tests, and the inspector's `public/data/` fallback
  all keep working during and after the migration.

## 3. Non-goals

- No schema migrations framework (we recreate the DB from scratch during
  Plan 08 and again whenever the schema changes; the dataset is
  re-derivable from `mmh/` + `cjk-decomp.json` + `extraction_plan.yaml`).
- No auth/RBAC beyond root/root.
- No remote/managed SurrealDB. `hanfont/olik` on local `127.0.0.1:6480`
  only.
- Bulk extraction for 500 chars (Plan 09), admin UI (Plan 10), and ComfyUI
  (Plan 11) are explicitly out of scope. The `style_variant` and
  `comfyui_job` tables are defined by Plan 08 but stay empty.

## 4. Architecture overview

```
          ┌──────────────────────────────────────────────┐
          │             SurrealDB 3.x (surrealkv)        │
          │        infra/surrealdb/data/  — hanfont/olik │
          └──────▲───────────────────▲───────────────▲───┘
                 │                   │               │
         Python  │           TS apps │    ComfyUI    │  (Plan 11)
         CLI     │           (Plan   │    job runner │
         `olik db│           10)     │               │
          sync`  │                   │               │
                 │                   │               │
    ┌────────────┴──────┐    ┌───────┴──────────┐  (future)
    │ olik_font.sink.   │    │ @olik/glyph-db   │
    │ surrealdb         │    │ (TS client pkg)  │
    │ (Python pkg)      │    │                  │
    └───────────────────┘    └──────────────────┘
```

- **`olik_font.sink.surrealdb`** (new Python module) — writes glyph records
  into SurrealDB, upsert-keyed on `glyph.char`. Consumed by a new CLI verb
  `olik db sync`.
- **`@olik/glyph-db`** (new TS workspace package) — typed query client that
  wraps `surrealdb.js`. Returned shapes validate against the existing
  `@olik/glyph-schema` Zod schemas. Consumed by inspector (Plan 10) and
  ComfyUI integration (Plan 11).
- **SurrealDB instance** — already running on 6480 with `surrealkv://
  infra/surrealdb/data` (established during brainstorming). Namespace
  `hanfont`, database `olik`.

## 5. Schema

### 5.1 Tables

| Table | Purpose | Key fields | Embedded fields |
|---|---|---|---|
| `glyph` | One row per Chinese character | `char` (unique), `stroke_count`, `radical`, `iou_mean`, `updated_at` | `stroke_instances[]`, `layout_tree`, `render_layers[]`, `iou_report` |
| `prototype` | Reusable stroke components | `id` (unique), `name`, `source`, `usage_count`, `created_at` | `strokes[]` |
| `rule` | Decomp / placement rules (from `rules.json`) | `id` (unique), `pattern`, `bucket`, `resolution` | — |
| `rule_trace` | Per-glyph record of rule firings | `glyph` (record link), `rule` (record link), `fired`, `order` | — |
| `extraction_run` | Ingest provenance | `started_at`, `finished_at`, `chars_processed`, `olik_version`, `mmh_commit`, `cjk_commit` | — |
| `style_variant` | ComfyUI-generated variants (Plan 11) | `glyph` (record link), `style_name`, `image_ref`, `workflow_id`, `status`, `generated_at` | — |
| `comfyui_job` | ComfyUI job tracking (Plan 11) | `id` (unique), `glyph` (record link), `style_name`, `status`, `progress`, `created_at`, `finished_at` | `workflow_spec` |

`stroke_instances`, `layout_tree`, `render_layers`, `iou_report` stay embedded
on `glyph` because they are never queried across glyphs. Embedding them keeps
one glyph = one write, matches the current JSON record shape, and avoids
write amplification.

### 5.2 Edges

Two RELATE-based edges give us the cross-glyph queries:

- `glyph -> uses -> prototype` — one edge per `component_instance` recorded
  on the glyph. Properties on the edge: `instance_id`, `position` (layout
  slot), `placed_bbox`.
- `glyph -> cites -> rule` — one edge per fired rule, carrying `order` and
  `alternative` (bool, true if the rule was considered but not chosen).

The `rule_trace` table is redundant with `glyph->cites->rule` edges. We keep
it anyway as an append-only log table — it preserves the order-within-a-run
information that graph edges don't, and it's cheap. Consumers can use
whichever is ergonomic.

### 5.3 Indexes

- `glyph.char` — UNIQUE, primary key-ish lookup
- `glyph.stroke_count` — range queries for admin UI filters
- `glyph.radical` — equality filter
- `glyph.iou_mean` — range queries (surface extraction failures)
- `prototype.id` — UNIQUE
- `prototype.name` — equality filter
- `style_variant.glyph + style_variant.style_name` — composite, for
  "variants of this glyph" listings

### 5.4 DDL sketch (SurrealQL)

```sql
DEFINE TABLE glyph SCHEMAFULL;
DEFINE FIELD char             ON glyph TYPE string ASSERT $value != NONE;
DEFINE FIELD stroke_count     ON glyph TYPE int;
DEFINE FIELD radical          ON glyph TYPE option<string>;
DEFINE FIELD iou_mean         ON glyph TYPE float;
DEFINE FIELD stroke_instances ON glyph TYPE array;
DEFINE FIELD layout_tree      ON glyph TYPE object;
DEFINE FIELD render_layers    ON glyph TYPE array;
DEFINE FIELD iou_report       ON glyph TYPE object;
DEFINE FIELD updated_at       ON glyph TYPE datetime DEFAULT time::now();
DEFINE INDEX glyph_char_uniq  ON glyph FIELDS char UNIQUE;
DEFINE INDEX glyph_stroke_ct  ON glyph FIELDS stroke_count;
DEFINE INDEX glyph_radical    ON glyph FIELDS radical;
DEFINE INDEX glyph_iou_mean   ON glyph FIELDS iou_mean;

DEFINE TABLE prototype SCHEMAFULL;
DEFINE FIELD id           ON prototype TYPE string ASSERT $value != NONE;
DEFINE FIELD name         ON prototype TYPE string;
DEFINE FIELD source       ON prototype TYPE option<string>;
DEFINE FIELD strokes      ON prototype TYPE array;
DEFINE FIELD usage_count  ON prototype TYPE int DEFAULT 0;
DEFINE FIELD created_at   ON prototype TYPE datetime DEFAULT time::now();
DEFINE INDEX proto_id_uniq ON prototype FIELDS id UNIQUE;

-- Edge tables are auto-created by RELATE but we pin schemas for safety.
DEFINE TABLE uses  SCHEMAFULL;
DEFINE FIELD instance_id ON uses TYPE string;
DEFINE FIELD position    ON uses TYPE option<string>;
DEFINE FIELD placed_bbox ON uses TYPE option<array>;

DEFINE TABLE cites SCHEMAFULL;
DEFINE FIELD order       ON cites TYPE int;
DEFINE FIELD alternative ON cites TYPE bool DEFAULT false;

-- rule, rule_trace, extraction_run, style_variant, comfyui_job
-- follow the same SCHEMAFULL pattern. Their full DEFINE blocks
-- are produced by `olik_font.sink.surrealdb.schema.DDL` and
-- exercised by the contract tests — the implementation plan
-- enumerates them task-by-task.
```

## 6. Python sink (`olik_font.sink.surrealdb`)

### 6.1 Package layout

```
project/py/src/olik_font/sink/
├── __init__.py
├── surrealdb.py        # main sink — upsert_glyph(), upsert_prototype()
├── schema.py           # DDL constant + ensure_schema(conn)
└── connection.py       # OLIK_DB_URL env → surrealdb.Surreal() factory
```

### 6.2 CLI changes

- `olik db sync <chars...>` — for each char, build the record (reusing
  existing `olik_font.emit` logic), open a SurrealDB transaction, upsert
  `glyph`, upsert any new `prototype` rows, delete old `uses`/`cites` edges
  for that glyph, insert fresh ones. One transaction per char.
- `olik db export --out <dir>` — reverse: query all glyphs/prototypes/rules,
  write JSON files matching the current on-disk format.
- `olik db reset` — DROP + recreate `hanfont/olik` and re-apply schema.
  Guard-railed with `--yes` flag; refuses to run against non-localhost DB.
- `olik build` keeps its current JSON behavior untouched (used by tests and
  by Plan 03's Archon workflows). Can be invoked with `--sync` to
  additionally push the result into SurrealDB.

### 6.3 Connection

Env var `OLIK_DB_URL` (default `http://root:root@127.0.0.1:6480`) plus
`OLIK_DB_NS` (default `hanfont`) and `OLIK_DB_NAME` (default `olik`). Python
side uses the official `surrealdb` pypi package, HTTP transport for
simplicity.

### 6.4 Idempotency contract

- `upsert_glyph(char, record)` must be safe to call repeatedly with the
  same input. Implemented via `UPDATE glyph:⟨char⟩ CONTENT $rec` (Surreal
  record-IDs are slug-form — we use `glyph:["明"]` literal).
- Edges are deleted-then-recreated within the same transaction to avoid
  stale `uses` after a glyph's component_instances change (e.g. after
  re-extraction).
- `extraction_run` is append-only: one row per CLI invocation.

## 7. TypeScript client package (`@olik/glyph-db`)

### 7.1 Package layout

```
project/ts/packages/glyph-db/
├── package.json        # workspace:* deps on @olik/glyph-schema
├── tsconfig.json
├── src/
│   ├── index.ts        # re-exports
│   ├── client.ts       # createDb() — thin wrapper over surrealdb.js
│   ├── queries.ts      # typed query helpers
│   └── types.ts        # GlyphSummary, StyleVariant, LiveHandle
└── test/
    ├── contract.test.ts   # sync-then-query round trip
    └── queries.test.ts    # query shape + pagination
```

### 7.2 Public API

```ts
export interface DbConfig {
  url: string;        // default ws://127.0.0.1:6480/rpc
  namespace: string;  // default "hanfont"
  database: string;   // default "olik"
  user: string;       // default "root"
  pass: string;       // default "root"
}

export function createDb(config?: Partial<DbConfig>): OlikDb;

export interface OlikDb {
  listGlyphs(opts?: {
    filter?:   { radical?: string; strokeCountRange?: [number, number]; iouBelow?: number };
    sort?:     "char" | "stroke_count" | "iou_mean";
    pageSize?: number;
    cursor?:   string;
  }): Promise<{ items: GlyphSummary[]; nextCursor?: string }>;

  getGlyph(char: string): Promise<GlyphRecord>;

  listPrototypes(): Promise<PrototypeSummary[]>;
  getPrototypeUsers(id: string): Promise<GlyphSummary[]>;

  listVariants(char: string): Promise<StyleVariant[]>;
  subscribeVariants(char: string, cb: (v: StyleVariant) => void): Unsubscribe;

  close(): Promise<void>;
}
```

`GlyphSummary` is a thin projection (`char`, `stroke_count`, `radical`,
`iou_mean`) to keep list queries cheap. `GlyphRecord` matches the existing
`@olik/glyph-schema` shape and is used by the detail drawer.

### 7.3 Live queries

`subscribeVariants` uses SurrealDB's `LIVE SELECT`. Plan 11 will use this to
stream ComfyUI results into the admin UI as they land. Plan 08 ships the
subscription API but has nothing producing variants yet; the test harness
inserts a row directly to prove the plumbing works.

## 8. Dev ergonomics (Taskfile)

New `task` targets added to the root `Taskfile.yml` (same file that already
hosts `task setup`, `task archon:run`, etc.):

- `task db:up` — idempotent; starts the persistent server if not running.
- `task db:down` — stop the server.
- `task db:reset` — stop, wipe `infra/surrealdb/data/`, restart, re-apply
  schema.
- `task db:seed` — run `olik db sync 明 清 國 森` against the running server.
- `task db:export` — `olik db export --out infra/surrealdb/snapshots/$(date +%Y-%m-%d)`.

## 9. Testing strategy

### 9.1 Python

- New pytest fixture `surreal_ephemeral` that runs `surreal start memory`
  on a random port per session, returns a connection, tears down at the
  end. Avoids clobbering the dev server.
- `test_sink_surrealdb_roundtrip` — sync a known record, query it back, assert
  equality (via Pydantic model, not raw dicts).
- `test_sink_idempotent` — sync → mutate one field → re-sync → assert no
  duplicate rows.
- `test_sink_prototype_edges` — assert `glyph->uses->prototype` edges exist
  with the right `instance_id` values.
- Existing `test_emit_*` tests keep working against JSON. No deletion.

### 9.2 TypeScript

- `@olik/glyph-db/test/contract.test.ts` — spins up `surreal start memory`
  via child_process, applies schema, inserts a fixture, asserts the
  typed API returns a validated record.
- `@olik/glyph-db/test/queries.test.ts` — sort, filter, pagination
  edge cases (empty result, single page, cursor handoff).
- The fixture record is the same `glyph-record-明.json` the Python suite
  uses, loaded as a constant so contracts cross the language boundary.

## 10. Migration plan (in-scope for Plan 08's implementation)

1. Stand up the SurrealDB schema via `ensure_schema()`.
2. `olik db sync 明 清 國 森` — ingest the existing 4 seed records.
3. Verify `olik db export --out /tmp/export` produces JSON byte-identical
   (modulo ordering) to `project/schema/examples/`.
4. Apps keep reading JSON for now — that transition is Plan 10's concern.

## 11. Risks & open questions

- **SurrealDB 3.x API surface is still evolving.** We pin to exactly
  `3.0.4` (the currently-running version) in both Python and TS deps, and
  document the upgrade path.
- **surrealkv write amplification** on re-extraction: deleting-then-
  recreating edges per glyph is a lot of churn. If that hurts, we can
  diff-and-upsert later. Out of scope for Plan 08.
- **Char as record ID.** `glyph:["明"]` is unicode-safe in SurrealDB 3.x but
  awkward to type. We could also hash it (e.g. `glyph:meng_01` with a
  separate `char` field). Design commits to the literal-char approach for
  readability in queries.
- **HTTP vs WebSocket transport.** Python uses HTTP (one transaction per
  request, fine for sync). TS uses WS (LIVE queries need it). This is a
  minor split but worth noting.
- **Backup.** `surreal export` is how you take a snapshot. `task db:export`
  also dumps JSON for human review. No automated periodic backup — user
  runs `task db:export` before any destructive schema work.

## 12. Out of scope / follow-up plans

- **Plan 09**: bulk extraction pipeline targeting 500 chars, auto-generated
  extraction plans from cjk-decomp + MMH, prototype library growth,
  human-in-loop review tooling.
- **Plan 10**: Refine or react-admin shell over `@olik/glyph-db`,
  virtualized list/grid, search/filter/sort, detail drawer embedding the
  existing inspector xyflow views.
- **Plan 11**: ComfyUI MVP — style generation workflow, job runner,
  variant ingestion, admin UI variant tab.
