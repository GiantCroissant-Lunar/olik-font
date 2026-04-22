---
title: "Plan 10 — Admin review UI (design)"
created: 2026-04-22
tags: [type/spec, topic/ui, topic/review]
status: draft
supersedes: null
relates-to:
  - "[[2026-04-21-surrealdb-foundation-design]]"
  - "[[2026-04-21-bulk-extraction-design]]"
  - "[[2026-04-22-variant-extraction-design]]"
  - "[[handover-2026-04-22-pm]]"
---

# Plan 10 — Admin review UI (design)

## 1. Context & motivation

Plan 09 populated the `glyph` table with auto-extracted rows triaged into
four statuses (`verified`, `needs_review`, `unsupported_op`,
`failed_extraction`). Plan 09.2 added the variant-extraction scaffolding
and confirmed via a 100-char smoke that the spec's assumption holds:
auto-extraction produces structurally-correct glyphs but cannot hit the
0.90 IoU gate on its own. The bottleneck for scaling to MoE 4808 is
**human triage of the `needs_review` bucket** — currently 64 chars out
of 100 sampled, and projected to be 2000-3000 at 4808 chars.

A human-in-the-loop reviewer cannot scale via the current `olik extract
list --status needs_review` CLI. Plan 10 delivers a browser UI that:

1. Surfaces the `needs_review` queue with thumbnails and one-keystroke
   approve/reject.
2. Renders each glyph's **composed output side-by-side with the MMH
   reference** so the reviewer can judge structural correctness at a
   glance.
3. Writes status transitions + optional review notes back to
   SurrealDB via a new `updateGlyphStatus` method on `@olik/glyph-db`.

Expected reviewer velocity: 2–3 seconds per char with keyboard-first
navigation, putting 4808 chars within a 3–4 hour review session.

## 2. Goals

- New TS app: `project/ts/apps/admin`, Refine + Mantine 9 + React 19.
- Workspace-wide React 18 → 19 upgrade as Task 1 of this plan (prereq
  for Mantine 9, which requires React 19.2+).
- Glyph list view: virtualized Mantine Table, filters on status / iou
  range / stroke_count / radical, default sort `iou_mean DESC` filtered
  to `status = needs_review`.
- Glyph detail view: split-panel layout with composed SVG (left),
  MMH reference SVG (right), metadata footer, keyboard-first
  approve/reject/skip/note flow.
- Three status transitions exposed in the UI, enforced client-side:
  - `Y` — approve: `needs_review` → `verified`
  - `N` — reject: `needs_review` → `failed_extraction` (`review_note`
    optional but recommended)
  - `J/K` — skip forward/back, no status change
- Extend `@olik/glyph-db`:
  - `ListFilter` gains `status` and `iouRange` fields.
  - New method `updateGlyphStatus(char, {newStatus, reviewNote?,
    reviewedBy?})` with client-side transition validation.
- Schema additions (optional fields on `glyph`): `review_note`,
  `reviewed_at`, `reviewed_by`.
- Stub `style_variant` resource in the admin app (reserved for Plan 11,
  returns empty list).

## 3. Non-goals

- ComfyUI integration, live `style_variant` streams — Plan 11.
- Structural edits (radical changes, prototype swaps, component
  re-picking) — Plan 12+.
- UI-triggered re-extraction ("retry with Plan 09.3 matcher") — Plan
  12+; for now, a reviewer who rejects a glyph can re-run `olik extract
  retry --status failed_extraction` after new extraction logic lands.
- Multi-user auth, per-user review attribution beyond `reviewed_by =
  process.env.USER`.
- Prototype library browser, rule editor, extraction-run dashboard — the
  admin app could grow these later, but Plan 10 scope is the reviewer
  queue only.
- Reports / exports / visualizations of review throughput.
- Plan 09.3 matcher improvements — tracked separately.

## 4. Architecture

```
┌────────────────────────────────────────────────────────────┐
│  project/ts/apps/admin/   (new, Refine + Mantine 9)        │
│                                                            │
│   src/App.tsx           Refine <Refine> root + router      │
│   src/data-provider.ts  Refine DataProvider over @olik/    │
│                         glyph-db (list/getOne/update)      │
│   src/auth-provider.ts  No-op (solo dev; root DB creds)    │
│   src/resources/                                           │
│     glyph/                                                 │
│       list.tsx         Mantine Table + filters + virt scroll│
│       detail.tsx       Split panel + keyboard shortcuts    │
│     style_variant/                                         │
│       list.tsx         Stub for Plan 11                    │
│   src/components/                                          │
│     GlyphSvg.tsx       Composed-output renderer            │
│     MmhSvg.tsx         Reference renderer (mmh strokes)    │
│     ReviewActions.tsx  Approve/Reject/Note/Skip            │
│                                                            │
└────────────────────────────────────────────────────────────┘
                              │
                              │  Refine hooks
                              │  (useList / useOne / useUpdate)
                              ▼
┌────────────────────────────────────────────────────────────┐
│  @olik/glyph-db  (existing, extended)                      │
│                                                            │
│   ListFilter: +status, +iouRange                           │
│   NEW:       updateGlyphStatus(char, ReviewUpdate)         │
│              - client-side VALID_TRANSITIONS check         │
│              - writes review_note + reviewed_at +          │
│                reviewed_by                                 │
│                                                            │
└────────────────────────────────────────────────────────────┘
                              │  WS rpc
                              ▼
                         SurrealDB (hanfont/olik)
```

Two data-flow characteristics worth calling out:

1. **Single source of truth.** The admin app reads live from SurrealDB
   via `@olik/glyph-db`'s WebSocket client (no intermediate cache, no
   localStorage). Refine's default `staleTime: 5s` is fine for the
   one-reviewer case; realtime subscriptions (LIVE queries) are not
   wired up in Plan 10.
2. **Direct writes.** `updateGlyphStatus` writes from the browser using
   the same root DB credentials the dev environment already uses
   (`127.0.0.1:6480`, root/root). No worker, no queue. Client-side
   transition validation guards against invalid state machine moves;
   a malicious or buggy caller can still bypass it by issuing raw
   `UPDATE` queries, but this is solo-dev local-host posture. Plan 11 or
   later can add an auth-provider if multi-user becomes a need.

## 5. React 19 upgrade (Plan 10 Task 1 / prereq)

Mantine 9 requires React 19.2+. Current workspace is on React 18.3.1.
Rather than pin the admin app to a divergent React version, Plan 10's
first task upgrades the entire TS workspace.

**Packages touched:**
- `@olik/flow-nodes`, `@olik/glyph-viz`, `@olik/rule-viz`,
  `@olik/glyph-db` (no React runtime; only types may move) — bump
  `@types/react`.
- `apps/inspector`, `apps/quickview`, `apps/remotion-studio` — bump
  `react`, `react-dom`, `@types/react`, `@types/react-dom`.
- Testing: verify `@testing-library/react` version (current 16.0.1);
  bump to ≥ 16.1 if React 19 exposes new test utilities we need.
  Baseline 16.0.1 is known to work with React 19 for the smoke-level
  tests Plan 10 writes.
- Vite: no bump required; `@vitejs/plugin-react` supports React 19 from
  v4+.

**Verification gate:** after the bump, `pnpm -r test` + `pnpm -r
typecheck` + `pnpm -r build` all green, and a manual smoke of
inspector + quickview + remotion-studio confirms no regressions. Only
after this passes does Plan 10 move to Task 2 (admin scaffold).

**Risk: `remotion-studio`.** Remotion tracks React closely; the bump
may surface Remotion compatibility issues. If remotion-studio fails
post-upgrade, fall back to pinning it to React 18 in its own
`package.json` (peer deps divergence is acceptable for a single app)
and note the issue as a Plan 11 cleanup item.

## 6. Reviewer workflow

### 6.1 Routing

Refine router:

- `/` — redirects to `/glyph`.
- `/glyph` — list view with filter bar + virtualized table.
- `/glyph/:char` — detail view.
- `/style_variant` — Plan 11 stub (empty list with "Reserved for Plan 11
  ComfyUI output" placeholder).

### 6.2 List view

- Virtualized Mantine Table using `@tanstack/react-virtual`. Visible
  rows ≤ viewport; 4808 rows scroll smoothly.
- Columns: `char` (rendered as SVG thumbnail from stroke data),
  `status` (Mantine badge), `iou_mean` (numeric, 3 decimals),
  `stroke_count`, `radical`, `extraction_run` (relative timestamp).
- Filter bar above the table: `status` multi-select, `iouRange` double
  slider (0–1), `strokeCountRange` double slider (1–30), `radical`
  text input.
- Default filter on page load: `status = needs_review`, sort
  `iou_mean DESC`.
- Click a row → `/glyph/:char`.

### 6.3 Detail view layout

```
┌─────────────────────────────────────────────────┐
│  [header: 林  iou=0.83  needs_review  Y/N/R/J/K]│
├───────────────────┬─────────────────────────────┤
│                   │                             │
│   composed SVG    │       MMH reference SVG     │
│   (our output)    │       (ground truth)        │
│                   │                             │
├───────────────────┴─────────────────────────────┤
│  components: 木 (canonical) + 木 (canonical)    │
│  stroke_count: 8   radical: 木                  │
│  extraction_run: <ts>   seed: 7                 │
│  review_note: [textarea]                        │
└─────────────────────────────────────────────────┘
```

Each SVG panel is 512×512 (same canonical coord space as the Python
renderer, with the y-flip applied at render time). The composed panel
uses `<GlyphSvg>` built from the row's `stroke_instances` field; the
MMH panel uses `<MmhSvg>` built from MMH's raw strokes for this char
(fetched once per detail view, keyed by char).

### 6.4 Keyboard shortcuts

Bound via Mantine `useHotkeys` when the detail view is focused.

| Key | Action |
|---|---|
| `J` | Next row in current filtered queue; no status change |
| `K` | Previous row; no status change |
| `Y` | Approve — transition to `verified`, auto-advance to next |
| `N` | Reject — transition to `failed_extraction`, auto-advance |
| `R` | Focus the `review_note` textarea |
| `F` | Toggle between current filter and "show all statuses" |
| `Esc` | Back to list view |
| `?` | Open keyboard cheat-sheet modal |

On `Y` / `N`, the UI calls `updateGlyphStatus` and optimistically
advances. If the write fails (rare — local WS), surface a Mantine
`notifications.show` with the error and keep the reviewer on the same
row.

### 6.5 Valid transitions enforced client-side

Mirrors `Status.VALID_TRANSITIONS` in Python (`bulk/status.py`):

```ts
export const VALID_TRANSITIONS: Record<Status, Set<Status>> = {
  unsupported_op:    new Set(["verified", "needs_review", "failed_extraction"]),
  failed_extraction: new Set(["verified", "needs_review", "unsupported_op"]),
  needs_review:      new Set(["verified", "needs_review", "failed_extraction"]),
  verified:          new Set(["verified", "needs_review", "failed_extraction"]),
};
```

`updateGlyphStatus` throws `InvalidTransition` if the combination is
not allowed. The UI disables buttons for invalid transitions rather
than relying on error recovery.

## 7. Schema changes

Additive; applied by `sink/schema.py::DDL` on next `ensure_schema()` run:

```sql
DEFINE FIELD review_note  ON glyph TYPE option<string>;
DEFINE FIELD reviewed_at  ON glyph TYPE option<datetime>;
DEFINE FIELD reviewed_by  ON glyph TYPE option<string>;
```

No index required; reviewers filter on `status`, which already has an
index from Plan 09 (§5.1).

`olik db export` gains round-trip coverage for the new fields — each
is already emitted naturally because the export path dumps the full
row JSON.

## 8. `@olik/glyph-db` changes

### 8.1 Types (`packages/glyph-db/src/types.ts`)

Additions:

```ts
export type Status =
  | "verified"
  | "needs_review"
  | "unsupported_op"
  | "failed_extraction";

export interface ListFilter {
  radical?: string;
  strokeCountRange?: [number, number];
  iouBelow?: number;        // existing
  iouRange?: [number, number];  // NEW
  status?: Status | Status[];   // NEW
}

export interface ReviewUpdate {
  newStatus: Status;
  reviewNote?: string | null;
  reviewedBy?: string;   // defaults to "browser" if omitted
}

export class InvalidTransition extends Error {
  constructor(public from: Status, public to: Status) {
    super(`invalid status transition: ${from} → ${to}`);
  }
}
```

Existing types (`GlyphSummary`, `ListOpts`, `ListPage`, etc.)
unchanged.

### 8.2 Queries (`packages/glyph-db/src/queries.ts`)

`buildListQuery` gains two new clauses: `status IN $status` (when
provided) and `iou_mean >= $iou_lo AND iou_mean <= $iou_hi` (when
`iouRange` provided).

New method on `OlikDb`:

```ts
async updateGlyphStatus(
  char: string,
  update: ReviewUpdate,
): Promise<void>
```

Implementation:

```ts
async updateGlyphStatus(char, update) {
  const current = await this.getGlyph(char);
  if (!current) throw new Error(`glyph not found: ${char}`);
  const currentStatus = current.status as Status;
  if (!VALID_TRANSITIONS[currentStatus].has(update.newStatus)) {
    throw new InvalidTransition(currentStatus, update.newStatus);
  }
  await raw.query(
    "UPDATE type::thing('glyph', $char) MERGE $patch;",
    {
      char,
      patch: {
        status: update.newStatus,
        review_note: update.reviewNote ?? null,
        reviewed_at: new Date().toISOString(),
        reviewed_by: update.reviewedBy ?? "browser",
      },
    },
  );
}
```

### 8.3 Client interface (`OlikDb`)

Adds `updateGlyphStatus` to the interface. `listGlyphs` signature
unchanged; new filters flow through `ListFilter`.

## 9. Refine DataProvider

File: `apps/admin/src/data-provider.ts`.

Maps Refine resource operations to `@olik/glyph-db`:

| Refine op | Resource | Implementation |
|---|---|---|
| `getList` | `glyph` | `db.listGlyphs({filter: mapFilters(params.filters), sort: mapSort(params.sorters), pageSize: params.pagination.pageSize, cursor: paginationCursor})` |
| `getOne` | `glyph` | `db.getGlyph(params.id as string)` — returns full GlyphRecord |
| `update` | `glyph` | `db.updateGlyphStatus(params.id, {newStatus: params.variables.status, reviewNote: params.variables.review_note, reviewedBy: currentUser()})` |
| `getList` | `style_variant` | returns `{data: [], total: 0}` — Plan 11 stub |
| `create`, `deleteOne`, `updateMany`, `custom` | any | throws `Not supported in Plan 10` |

Refine filter mapping: Refine ships `CrudFilters` with `field`,
`operator`, `value`. We translate:

- `field: "status", operator: "in" | "eq"` → `ListFilter.status`
- `field: "iou_mean", operator: "between"` → `ListFilter.iouRange`
- `field: "stroke_count", operator: "between"` →
  `ListFilter.strokeCountRange`
- `field: "radical", operator: "eq"` → `ListFilter.radical`

Any unsupported filter combination is logged to console and ignored
(no silent misbehavior — the filter bar UI only emits the supported
shapes above).

`currentUser()` returns `import.meta.env.VITE_REVIEWER ?? "browser"`,
writeable via a `.env.local` file in `apps/admin/`.

## 10. Testing strategy

### 10.1 Unit — admin app (vitest + @testing-library/react 16.x)

- `data-provider.test.ts`:
  - Mocked `OlikDb`; each Refine operation maps correctly.
  - Unsupported operations throw.
  - Filter shape mapping is lossless (round-trip assertions).
- `review-actions.test.tsx`:
  - `Y` fires `updateGlyphStatus(char, {newStatus: "verified"})`.
  - `N` fires `updateGlyphStatus(char, {newStatus: "failed_extraction"})`
    with optional review_note from the textarea value.
  - `J/K` don't write; they advance list index only.
  - Invalid transitions disable the button (e.g. a `verified` row
    shown in review mode doesn't allow `Y` → `verified` self-transition
    — button shows as "Already verified").
- `glyph-list.test.tsx`:
  - Default filter emits `{status: "needs_review"}` to data provider.
  - Filter bar widgets map to the correct `ListFilter` shape.
  - Virtualized table renders the visible-window count only (no
    pathological full-list render).

### 10.2 Unit — @olik/glyph-db

Extend `packages/glyph-db/src/__tests__` (or add):

- `updateGlyphStatus` with a mocked Surreal:
  - Happy path writes the expected UPDATE query + params.
  - `InvalidTransition` raised for disallowed combos.
  - Missing char raises "glyph not found".
- `buildListQuery` tests extended to cover `status` and `iouRange`.

### 10.3 Integration — Python pytest (ephemeral SurrealDB)

- `tests/test_admin_schema_roundtrip.py` (new):
  - `ensure_schema()` applies the three new fields.
  - `upsert_glyph` with `review_note` / `reviewed_at` / `reviewed_by`
    round-trips via `olik db export`.

### 10.4 Manual E2E smoke

Documented in Plan 10 Task 9 (last task, analogous to Plan 09.2 Task 9):

1. `task db:reset && task db:seed` then `olik extract auto --count 20`.
2. `pnpm --filter @olik/admin dev`; open `http://localhost:5173/`.
3. Review 5 chars via keyboard shortcuts.
4. Run `olik extract report`; verify counts shift as expected.
5. Reload admin; verify `reviewed_at` and `reviewed_by` populated on the
   reviewed rows.

## 11. Risks & open questions

- **React 19 upgrade surface area.** `remotion-studio` is the highest-
  risk app. Mitigation: if Remotion doesn't support React 19 at upgrade
  time, pin it to React 18 via its own peer-deps and document in the
  Plan 10 commit.
- **Mantine 9 maturity.** v9.1.0 landed 2026-04-21; early-v9 rough edges
  are plausible. Mitigation: admin app is small, components used are
  stable across v8/v9 (Table, Drawer, TextInput, Badge, useHotkeys).
  Refine's `@refinedev/mantine` v7+ tracks Mantine 9.
- **Browser WebSocket connection to SurrealDB.** `@olik/glyph-db`
  already connects via WS; no new network concern. If the reviewer
  leaves the tab idle for >30 min, the connection may drop; Refine's
  retry on next action handles it but may show a transient error.
- **SurrealDB UPDATE contention.** Single-reviewer posture means no
  conflicts. If two reviewers ever touched the same row, SurrealDB's
  last-write-wins is fine for our use case.
- **Client-side transition enforcement bypass.** A user opening
  browser devtools and issuing raw `UPDATE` queries can bypass the
  state machine. Documented in §4; Plan 11+ adds an auth provider +
  server-side enforcement if needed.
- **Reviewer UX for ambiguous cases.** When a glyph "looks kind of
  right" the reviewer may want to defer. `J/K` skip serves this —
  the row stays `needs_review` and the reviewer can return later. No
  explicit "defer" state needed.
- **Existing SVG renderers.** `GlyphSvg` needs to accept a
  `GlyphRecord` from SurrealDB (same shape the Python sink writes).
  `quickview/src/glyph-svg.tsx` is the reference implementation; we
  either factor it into `@olik/glyph-viz` (shared) or copy into
  `apps/admin/src/components/`. Factor into shared package if the copy
  would be >50 lines — Plan 10's implementation plan picks one.

## 12. Out of scope / follow-up plans

- **Plan 11** — ComfyUI style_variant generation + LIVE subscription
  in the admin's `/style_variant` tab. First use of Refine's
  realtime support in this app.
- **Plan 12** — Unsupported operator coverage (expand the `OP_TO_MODE`
  LUT for `stl`, `st`, `sl`, `str`, `lock`, `me`, `w`, `wtl`, `d/t`,
  `d/m`, `sbl`, `wd`, `rrefl`, `ra`). Admin's `unsupported_op` filter
  exposes which ops need adding first.
- **Plan 12+** — UI-triggered re-extraction, structural edits,
  prototype library browser, extraction-run dashboard. The admin's
  bones support adding these as Refine resources.
- **Plan 09.3** — Matcher upgrade (shape/median-based similarity) to
  lift `verified` share. Admin will surface the lift naturally (fewer
  `needs_review` rows), no code change.
- **Multi-user auth + audit.** Current `reviewed_by` is solo-dev; a
  future plan can add SurrealDB user records + per-row permissions.

## 13. Migration / compatibility

- Schema changes are additive (`option<string>` / `option<datetime>`) —
  existing rows get `NONE` values; no data migration.
- React 19 bump is the only breaking dep change. Verified per §5.
- `@olik/glyph-db` API extensions are additive (new optional filter
  fields + new method); existing callers (Python doesn't call this;
  no TS consumers yet outside admin) unaffected.
- `olik db export` picks up the new fields automatically since it
  dumps full row JSON.

Plan 10 ships as a single squash-merged PR via Archon workflow
`plan-10-admin-review-ui`, mirroring Plan 09.2's pattern with the
same `create_pr --body-file` safety fix.
