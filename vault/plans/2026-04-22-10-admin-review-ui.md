---
title: "Plan 10 — Admin review UI (implementation plan)"
created: 2026-04-22
tags: [type/plan, topic/ui, topic/review]
status: ready
relates-to:
  - "[[2026-04-22-admin-review-ui-design]]"
  - "[[handover-2026-04-22-pm]]"
---

# Plan 10 — Admin review UI (implementation plan)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a browser-based reviewer queue (`project/ts/apps/admin`) that surfaces the SurrealDB `needs_review` bucket and records `approve`/`reject` decisions back to the DB via a new `updateGlyphStatus` write on `@olik/glyph-db`.

**Architecture:** Refine + Mantine 9 app on React 19. A thin DataProvider wraps the existing `@olik/glyph-db` client (extended with `status`/`iouRange` filters and `updateGlyphStatus`). Glyph rows gain `mmh_strokes` on the Python sink side so the browser can render the MMH reference without fetching MMH's 28MB JSONL. Reviewer navigates via keyboard (`J/K/Y/N/R/Esc`) through a split-panel detail view showing composed SVG vs MMH reference.

**Tech Stack:** React 19.0.x, Mantine 9.1+, @refinedev/core 4.x, @refinedev/mantine, @tanstack/react-virtual, Vite 5.4.x, Vitest 2.1.x, @testing-library/react 16.1+. SurrealDB WS client via @olik/glyph-db (surrealdb 2.x).

**Spec:** [[2026-04-22-admin-review-ui-design]] — commit `2de0ded`.

---

## File plan

**Create:**
- `project/ts/apps/admin/package.json`
- `project/ts/apps/admin/tsconfig.json`
- `project/ts/apps/admin/vite.config.ts`
- `project/ts/apps/admin/index.html`
- `project/ts/apps/admin/src/main.tsx`
- `project/ts/apps/admin/src/App.tsx`
- `project/ts/apps/admin/src/data-provider.ts`
- `project/ts/apps/admin/src/auth-provider.ts`
- `project/ts/apps/admin/src/resources/glyph/list.tsx`
- `project/ts/apps/admin/src/resources/glyph/detail.tsx`
- `project/ts/apps/admin/src/resources/style_variant/list.tsx`
- `project/ts/apps/admin/src/components/GlyphSvg.tsx`
- `project/ts/apps/admin/src/components/MmhSvg.tsx`
- `project/ts/apps/admin/src/components/ReviewActions.tsx`
- `project/ts/apps/admin/src/components/GlyphThumb.tsx`
- `project/ts/apps/admin/src/__tests__/data-provider.test.ts`
- `project/ts/apps/admin/src/__tests__/review-actions.test.tsx`
- `project/ts/apps/admin/src/__tests__/glyph-list.test.tsx`
- `project/ts/packages/glyph-db/src/__tests__/update-glyph-status.test.ts`
- `project/ts/packages/glyph-db/src/__tests__/list-filter.test.ts`
- `project/py/tests/test_sink_mmh_strokes.py`

**Modify:**
- `project/ts/apps/inspector/package.json` — bump React 18 → 19
- `project/ts/apps/quickview/package.json` — bump React 18 → 19
- `project/ts/apps/remotion-studio/package.json` — bump React 18 → 19
- `project/ts/packages/flow-nodes/package.json` — bump `@types/react`
- `project/ts/packages/glyph-viz/package.json` — bump `@types/react`
- `project/ts/packages/rule-viz/package.json` — bump `@types/react`
- `project/ts/packages/glyph-db/src/types.ts` — add Status, VALID_TRANSITIONS, ReviewUpdate, InvalidTransition; extend ListFilter
- `project/ts/packages/glyph-db/src/queries.ts` — filter extensions + `updateGlyphStatus`
- `project/ts/packages/glyph-db/src/client.ts` — interface update
- `project/py/src/olik_font/emit/record.py` — embed mmh strokes in built record
- `project/py/src/olik_font/bulk/batch.py` — pass mmh strokes through _db_record

---

## Task 1: Workspace React 18 → 19 upgrade

**Files:**
- Modify: `project/ts/apps/inspector/package.json`
- Modify: `project/ts/apps/quickview/package.json`
- Modify: `project/ts/apps/remotion-studio/package.json`
- Modify: `project/ts/packages/flow-nodes/package.json`
- Modify: `project/ts/packages/glyph-viz/package.json`
- Modify: `project/ts/packages/rule-viz/package.json`

- [ ] **Step 1: Bump React + @types in all three apps**

In each of `project/ts/apps/{inspector,quickview,remotion-studio}/package.json`, change:

```json
"react": "19.0.0",
"react-dom": "19.0.0",
```

and in `devDependencies`:

```json
"@types/react": "19.0.0",
"@types/react-dom": "19.0.0",
"@testing-library/react": "^16.1.0",
```

Keep every other dep at its current version.

- [ ] **Step 2: Bump `@types/react` in packages that carry React types**

In each of `project/ts/packages/{flow-nodes,glyph-viz,rule-viz}/package.json`, change:

```json
"@types/react": "19.0.0",
"@types/react-dom": "19.0.0",
```

(Only the dev entry. These packages don't have a `react` runtime dep — they're type-only for React. Leave `peerDependencies` pinned at `^18 || ^19` if present, or add it if absent so the package advertises React 19 compatibility.)

- [ ] **Step 3: Install and verify pnpm resolution**

Run: `cd project/ts && pnpm install 2>&1 | tail -15`
Expected: `Progress: resolved N, reused M, downloaded K, added J` with no `ERR_PNPM_PEER_DEP_ISSUES` on React.

If pnpm reports peer-dep issues on `@xyflow/react`, `@remotion/*`, or another consumer, check that package's React peerDep range. `@xyflow/react@12.3.5` accepts React 18 and 19. If `@remotion/*` declines React 19, stop and pin `apps/remotion-studio` back to React 18 by reverting its three fields (only that app); record the downgrade in the commit message. The other apps stay on React 19.

- [ ] **Step 4: Run the full workspace test + typecheck + build**

Run: `cd project/ts && pnpm -r test 2>&1 | tail -20`
Expected: every package passes; no test file fails with "Cannot use React 19 with ..." errors.

Run: `cd project/ts && pnpm -r typecheck 2>&1 | tail -20`
Expected: zero TS errors.

Run: `cd project/ts && pnpm -r --filter '!@olik/remotion-studio' build 2>&1 | tail -10`
Expected: all packages build cleanly. (remotion-studio is excluded from `-r build` per existing convention; still subject to typecheck above.)

- [ ] **Step 5: Commit**

```bash
git add project/ts/apps/inspector/package.json \
        project/ts/apps/quickview/package.json \
        project/ts/apps/remotion-studio/package.json \
        project/ts/packages/flow-nodes/package.json \
        project/ts/packages/glyph-viz/package.json \
        project/ts/packages/rule-viz/package.json \
        project/ts/pnpm-lock.yaml
git commit -m "chore(ts): bump workspace React 18.3 -> 19.0 (Plan 10 prereq)"
```

---

## Task 2: @olik/glyph-db — filter extensions (status + iouRange)

**Files:**
- Modify: `project/ts/packages/glyph-db/src/types.ts`
- Modify: `project/ts/packages/glyph-db/src/queries.ts`
- Create: `project/ts/packages/glyph-db/src/__tests__/list-filter.test.ts`

- [ ] **Step 1: Write the failing test**

Create `project/ts/packages/glyph-db/src/__tests__/list-filter.test.ts`:

```ts
import { describe, it, expect } from "vitest";
import { buildListQuery } from "../queries.js";

describe("buildListQuery", () => {
  it("includes status clause when filter.status is a single value", () => {
    const { sql, bind } = buildListQuery({ filter: { status: "needs_review" } });
    expect(sql).toContain("status IN $status");
    expect(bind.status).toEqual(["needs_review"]);
  });

  it("accepts status as an array of values", () => {
    const { sql, bind } = buildListQuery({
      filter: { status: ["needs_review", "failed_extraction"] },
    });
    expect(sql).toContain("status IN $status");
    expect(bind.status).toEqual(["needs_review", "failed_extraction"]);
  });

  it("applies iouRange as a between clause", () => {
    const { sql, bind } = buildListQuery({ filter: { iouRange: [0.5, 0.9] } });
    expect(sql).toContain("iou_mean >= $iou_lo AND iou_mean <= $iou_hi");
    expect(bind.iou_lo).toBe(0.5);
    expect(bind.iou_hi).toBe(0.9);
  });

  it("combines multiple filters with AND", () => {
    const { sql } = buildListQuery({
      filter: { status: "needs_review", iouRange: [0.5, 0.9], strokeCountRange: [5, 15] },
    });
    expect(sql).toMatch(/WHERE .+ AND .+ AND .+/);
  });

  it("keeps iouBelow back-compat working alongside iouRange", () => {
    const { sql, bind } = buildListQuery({ filter: { iouBelow: 0.75 } });
    expect(sql).toContain("iou_mean < $iou");
    expect(bind.iou).toBe(0.75);
  });
});
```

Note: this test requires `buildListQuery` to be exported from `queries.ts`. Add the export in Step 3.

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd project/ts/packages/glyph-db && pnpm test -- --run list-filter.test 2>&1 | tail -20`
Expected: fails with "buildListQuery is not exported" or similar.

- [ ] **Step 3: Add `Status` type and extended `ListFilter`**

Edit `project/ts/packages/glyph-db/src/types.ts`. Add at the top (after existing imports):

```ts
export type Status =
  | "verified"
  | "needs_review"
  | "unsupported_op"
  | "failed_extraction";

export const STATUS_VALUES: readonly Status[] = [
  "verified",
  "needs_review",
  "unsupported_op",
  "failed_extraction",
] as const;
```

Extend the existing `ListFilter`:

```ts
export type ListFilter = {
  radical?: string;
  strokeCountRange?: [number, number];
  iouBelow?: number;
  iouRange?: [number, number];
  status?: Status | Status[];
};
```

- [ ] **Step 4: Update `buildListQuery` in queries.ts**

Edit `project/ts/packages/glyph-db/src/queries.ts`. Change `function buildListQuery` to `export function buildListQuery`, and inside the function, after the existing `iouBelow` clause and before the `where` computation, add:

```ts
if (f.iouRange !== undefined) {
  clauses.push("iou_mean >= $iou_lo AND iou_mean <= $iou_hi");
  bind.iou_lo = f.iouRange[0];
  bind.iou_hi = f.iouRange[1];
}
if (f.status !== undefined) {
  clauses.push("status IN $status");
  bind.status = Array.isArray(f.status) ? f.status : [f.status];
}
```

- [ ] **Step 5: Run tests and typecheck**

Run: `cd project/ts/packages/glyph-db && pnpm test 2>&1 | tail -10`
Expected: all tests pass (5 new + any previously existing).

Run: `cd project/ts/packages/glyph-db && pnpm typecheck 2>&1 | tail -10`
Expected: no errors.

- [ ] **Step 6: Commit**

```bash
git add project/ts/packages/glyph-db/src/types.ts \
        project/ts/packages/glyph-db/src/queries.ts \
        project/ts/packages/glyph-db/src/__tests__/list-filter.test.ts
git commit -m "feat(glyph-db): ListFilter gains status + iouRange"
```

---

## Task 3: @olik/glyph-db — updateGlyphStatus

**Files:**
- Modify: `project/ts/packages/glyph-db/src/types.ts`
- Modify: `project/ts/packages/glyph-db/src/queries.ts`
- Modify: `project/ts/packages/glyph-db/src/client.ts`
- Modify: `project/ts/packages/glyph-db/src/index.ts`
- Create: `project/ts/packages/glyph-db/src/__tests__/update-glyph-status.test.ts`

- [ ] **Step 1: Write the failing test**

Create `project/ts/packages/glyph-db/src/__tests__/update-glyph-status.test.ts`:

```ts
import { describe, it, expect, vi } from "vitest";
import { makeQueries } from "../queries.js";
import { InvalidTransition } from "../types.js";

function mockSurreal(getRows: unknown, updateSpy: ReturnType<typeof vi.fn>) {
  return {
    query: vi.fn().mockImplementation((sql: string) => {
      if (sql.startsWith("SELECT * FROM glyph")) {
        return {
          collect: async () => [[getRows]],
        };
      }
      if (sql.startsWith("UPDATE type::thing")) {
        return {
          collect: async () => {
            updateSpy(sql);
            return [[{}]];
          },
        };
      }
      throw new Error(`unexpected SQL: ${sql}`);
    }),
  } as unknown as Parameters<typeof makeQueries>[0];
}

describe("updateGlyphStatus", () => {
  it("writes status + review_note + reviewed_at + reviewed_by on a valid transition", async () => {
    const updateSpy = vi.fn();
    const raw = mockSurreal([{ char: "林", status: "needs_review" }], updateSpy);
    const db = makeQueries(raw);
    await db.updateGlyphStatus("林", {
      newStatus: "verified",
      reviewNote: "looks good",
      reviewedBy: "alice",
    });
    expect(updateSpy).toHaveBeenCalledTimes(1);
    const callArgs = (raw.query as ReturnType<typeof vi.fn>).mock.calls.at(-1)!;
    expect(callArgs[1].patch.status).toBe("verified");
    expect(callArgs[1].patch.review_note).toBe("looks good");
    expect(callArgs[1].patch.reviewed_by).toBe("alice");
    expect(typeof callArgs[1].patch.reviewed_at).toBe("string");
  });

  it("defaults reviewedBy to 'browser' and accepts null review_note", async () => {
    const updateSpy = vi.fn();
    const raw = mockSurreal([{ char: "林", status: "needs_review" }], updateSpy);
    const db = makeQueries(raw);
    await db.updateGlyphStatus("林", { newStatus: "failed_extraction" });
    const callArgs = (raw.query as ReturnType<typeof vi.fn>).mock.calls.at(-1)!;
    expect(callArgs[1].patch.reviewed_by).toBe("browser");
    expect(callArgs[1].patch.review_note).toBeNull();
  });

  it("throws InvalidTransition when the target is not in VALID_TRANSITIONS[current]", async () => {
    const updateSpy = vi.fn();
    // verified → unsupported_op is not allowed under the mirrored Python rules
    // (see Plan 10 spec §6.5).
    const raw = mockSurreal([{ char: "林", status: "verified" }], updateSpy);
    const db = makeQueries(raw);
    await expect(
      db.updateGlyphStatus("林", { newStatus: "unsupported_op" }),
    ).rejects.toBeInstanceOf(InvalidTransition);
    expect(updateSpy).not.toHaveBeenCalled();
  });

  it("throws when the glyph does not exist", async () => {
    const updateSpy = vi.fn();
    const raw = mockSurreal(undefined, updateSpy);
    const db = makeQueries(raw);
    await expect(
      db.updateGlyphStatus("XX", { newStatus: "verified" }),
    ).rejects.toThrow(/not found/);
    expect(updateSpy).not.toHaveBeenCalled();
  });
});
```

- [ ] **Step 2: Run to confirm it fails**

Run: `cd project/ts/packages/glyph-db && pnpm test -- --run update-glyph-status 2>&1 | tail -20`
Expected: fails on import error (InvalidTransition not exported) or missing method.

- [ ] **Step 3: Add types + transitions in types.ts**

Edit `project/ts/packages/glyph-db/src/types.ts`, append:

```ts
export interface ReviewUpdate {
  newStatus: Status;
  reviewNote?: string | null;
  reviewedBy?: string;
}

export class InvalidTransition extends Error {
  constructor(public readonly from: Status, public readonly to: Status) {
    super(`invalid status transition: ${from} -> ${to}`);
    this.name = "InvalidTransition";
  }
}

/**
 * Mirrors `olik_font.bulk.status.Status.VALID_TRANSITIONS` semantics.
 * Plan 09.1 permits every transition; Plan 10's UI only issues
 * `needs_review -> verified|failed_extraction`, but client-side
 * enforcement is strict so future UI paths can't silently regress.
 * Self-transitions are included so idempotent writes don't throw.
 */
export const VALID_TRANSITIONS: Record<Status, ReadonlySet<Status>> = {
  verified: new Set(["verified", "needs_review", "failed_extraction"]),
  needs_review: new Set(["verified", "needs_review", "failed_extraction"]),
  unsupported_op: new Set([
    "verified",
    "needs_review",
    "failed_extraction",
    "unsupported_op",
  ]),
  failed_extraction: new Set([
    "verified",
    "needs_review",
    "failed_extraction",
    "unsupported_op",
  ]),
};
```

- [ ] **Step 4: Add `updateGlyphStatus` to client.ts interface**

Edit `project/ts/packages/glyph-db/src/client.ts`. Extend the `OlikDb` interface (insert after `listVariants`):

```ts
updateGlyphStatus(char: string, update: ReviewUpdate): Promise<void>;
```

Add the import at the top of the file:

```ts
import type {
  GlyphSummary,
  ListOpts,
  ListPage,
  PrototypeSummary,
  ReviewUpdate,
  StyleVariant,
  Unsubscribe,
} from "./types.js";
```

- [ ] **Step 5: Implement `updateGlyphStatus` in queries.ts**

Edit `project/ts/packages/glyph-db/src/queries.ts`. Add imports at the top:

```ts
import {
  InvalidTransition,
  VALID_TRANSITIONS,
  type ReviewUpdate,
  type Status,
} from "./types.js";
```

Add the method inside the object returned by `makeQueries` (after `subscribeVariants`, before `close`):

```ts
async updateGlyphStatus(char: string, update: ReviewUpdate): Promise<void> {
  const [rows = []] = await raw
    .query("SELECT * FROM glyph WHERE char = $c;", { c: char })
    .collect<[Array<{ status?: string }>]>();
  const existing = rows[0];
  if (existing === undefined) {
    throw new Error(`glyph not found: ${char}`);
  }
  const currentStatus = (existing.status ?? "needs_review") as Status;
  if (!VALID_TRANSITIONS[currentStatus]?.has(update.newStatus)) {
    throw new InvalidTransition(currentStatus, update.newStatus);
  }
  await raw
    .query(
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
    )
    .collect();
},
```

- [ ] **Step 6: Re-export the new symbols from index.ts**

Edit `project/ts/packages/glyph-db/src/index.ts`. Add to the `export type` block:

```ts
export type {
  GlyphSummary,
  PrototypeSummary,
  StyleVariant,
  ListFilter,
  ListOpts,
  ListPage,
  Unsubscribe,
  GlyphRecord,
  Prototype,
  Status,
  ReviewUpdate,
} from "./types.js";
export { InvalidTransition, VALID_TRANSITIONS, STATUS_VALUES } from "./types.js";
```

- [ ] **Step 7: Run tests and typecheck**

Run: `cd project/ts/packages/glyph-db && pnpm test 2>&1 | tail -10`
Expected: all pass (4 new + prior).

Run: `cd project/ts/packages/glyph-db && pnpm typecheck 2>&1 | tail -5`
Expected: no errors.

Run: `cd project/ts/packages/glyph-db && pnpm build 2>&1 | tail -5`
Expected: `dist/` populated; no tsup errors.

- [ ] **Step 8: Commit**

```bash
git add project/ts/packages/glyph-db/src/types.ts \
        project/ts/packages/glyph-db/src/queries.ts \
        project/ts/packages/glyph-db/src/client.ts \
        project/ts/packages/glyph-db/src/index.ts \
        project/ts/packages/glyph-db/src/__tests__/update-glyph-status.test.ts
git commit -m "feat(glyph-db): updateGlyphStatus with VALID_TRANSITIONS enforcement"
```

---

## Task 4: Python sink — embed mmh_strokes on glyph rows

**Files:**
- Modify: `project/py/src/olik_font/emit/record.py`
- Modify: `project/py/src/olik_font/bulk/batch.py`
- Create: `project/py/tests/test_sink_mmh_strokes.py`

The admin's detail view renders composed-vs-MMH side-by-side. Rather than fetching MMH's ~28MB `graphics.txt` JSONL in the browser, we embed the char's MMH stroke path-d strings on the glyph row at extract time. One copy per glyph; zero new network infra.

- [ ] **Step 1: Write the failing test**

Create `project/py/tests/test_sink_mmh_strokes.py`:

```python
"""Plan 10: glyph rows carry mmh_strokes for browser-side reference render."""

from __future__ import annotations

from olik_font.emit.record import build_glyph_record
from olik_font.prototypes.extraction_plan import (
    GlyphNodePlan,
    GlyphPlan,
    PrototypePlan,
)
from olik_font.types import MmhChar, PrototypeLibrary


def _mmh(strokes: list[str]) -> MmhChar:
    return MmhChar(character="X", strokes=strokes, medians=[[]] * len(strokes))


def test_build_glyph_record_embeds_mmh_strokes() -> None:
    """The emit path writes the MMH stroke path-d strings onto the
    record so the browser renders the reference view without fetching
    the source JSONL.
    """
    mmh_paths = ["M0,0 L100,100", "M100,100 L200,200"]
    record = build_glyph_record(
        "X",
        resolved=[],
        constraints=(),
        library=PrototypeLibrary(),
        mmh_char=_mmh(mmh_paths),
    )
    assert record.get("mmh_strokes") == mmh_paths


def test_build_glyph_record_mmh_strokes_is_tuple_or_list() -> None:
    """Downstream JSON serialization needs list-or-tuple; not a custom type."""
    record = build_glyph_record(
        "X",
        resolved=[],
        constraints=(),
        library=PrototypeLibrary(),
        mmh_char=_mmh(["M0,0"]),
    )
    assert isinstance(record["mmh_strokes"], (list, tuple))
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd project/py && .venv/bin/pytest tests/test_sink_mmh_strokes.py -v 2>&1 | tail -10`
Expected: both tests fail with `AssertionError: record.get("mmh_strokes") is None`.

- [ ] **Step 3: Update `build_glyph_record` to embed `mmh_strokes`**

Open `project/py/src/olik_font/emit/record.py` to locate the return-dict assembly. At the place the function builds the final dict, add a new key:

```python
"mmh_strokes": list(mmh_char.strokes),
```

Pair it next to existing `mmh_char`-derived fields. If the function currently returns a dict literal that doesn't reference `mmh_char.strokes`, insert the key before `return` and keep it alphabetically-grouped with the other stroke-related fields.

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd project/py && .venv/bin/pytest tests/test_sink_mmh_strokes.py -v 2>&1 | tail -10`
Expected: both tests pass.

- [ ] **Step 5: Full py suite regression check**

Run: `cd project/py && .venv/bin/pytest -q 2>&1 | tail -6`
Expected: all prior tests still pass + 2 new. Current baseline is 162 passed, 1 xfailed; new baseline should be 164 passed, 1 xfailed.

- [ ] **Step 6: Commit**

```bash
git add project/py/src/olik_font/emit/record.py \
        project/py/tests/test_sink_mmh_strokes.py
git commit -m "feat(emit): embed mmh_strokes on glyph record for admin reference view"
```

---

## Task 5: Admin app scaffold

**Files:**
- Create: `project/ts/apps/admin/package.json`
- Create: `project/ts/apps/admin/tsconfig.json`
- Create: `project/ts/apps/admin/vite.config.ts`
- Create: `project/ts/apps/admin/index.html`
- Create: `project/ts/apps/admin/src/main.tsx`
- Create: `project/ts/apps/admin/src/App.tsx`

This task scaffolds an empty Refine + Mantine 9 shell that renders "Plan 10 admin" and nothing else. Later tasks add the data provider and resources.

- [ ] **Step 1: Create package.json**

Create `project/ts/apps/admin/package.json`:

```json
{
  "name": "@olik/admin",
  "version": "0.1.0",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview",
    "test": "vitest run",
    "typecheck": "tsc --noEmit"
  },
  "dependencies": {
    "@mantine/core": "^9.1.0",
    "@mantine/hooks": "^9.1.0",
    "@mantine/notifications": "^9.1.0",
    "@olik/glyph-db": "workspace:*",
    "@olik/glyph-schema": "workspace:*",
    "@refinedev/core": "^4.55.0",
    "@refinedev/mantine": "^3.0.0",
    "@refinedev/react-router": "^1.0.0",
    "@tabler/icons-react": "^3.0.0",
    "@tanstack/react-virtual": "^3.0.0",
    "react": "19.0.0",
    "react-dom": "19.0.0",
    "react-router": "^7.0.0"
  },
  "devDependencies": {
    "@testing-library/react": "^16.1.0",
    "@types/react": "19.0.0",
    "@types/react-dom": "19.0.0",
    "@vitejs/plugin-react": "^4.3.3",
    "jsdom": "25.0.1",
    "typescript": "5.6.3",
    "vite": "5.4.9",
    "vitest": "2.1.2"
  }
}
```

If `@refinedev/mantine` has not yet published a Mantine-9-compatible release at implementation time, pin `@mantine/*` to `^8.3.18` and keep the React 19 bump — Mantine 8 supports React 19 as of its 8.3.x line. Adjust the other @mantine deps accordingly and make a note in the commit message.

- [ ] **Step 2: Create tsconfig.json**

Create `project/ts/apps/admin/tsconfig.json`:

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["ES2022", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "moduleResolution": "bundler",
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "isolatedModules": true,
    "resolveJsonModule": true,
    "types": ["vitest/globals"]
  },
  "include": ["src"]
}
```

- [ ] **Step 3: Create vite.config.ts**

Create `project/ts/apps/admin/vite.config.ts`:

```ts
import { resolve } from "node:path";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@olik/glyph-db":     resolve(__dirname, "../../packages/glyph-db/src/index.ts"),
      "@olik/glyph-schema": resolve(__dirname, "../../packages/glyph-schema/src/index.ts"),
    },
  },
  server: { port: 5174 },
  test: { environment: "jsdom", globals: true },
});
```

Port 5174 avoids clashing with inspector (5173) and quickview.

- [ ] **Step 4: Create index.html**

Create `project/ts/apps/admin/index.html`:

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>olik admin</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 5: Create src/main.tsx and App.tsx**

Create `project/ts/apps/admin/src/main.tsx`:

```tsx
import "@mantine/core/styles.css";
import "@mantine/notifications/styles.css";

import React from "react";
import ReactDOM from "react-dom/client";
import { MantineProvider } from "@mantine/core";
import { Notifications } from "@mantine/notifications";

import { App } from "./App.js";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <MantineProvider defaultColorScheme="auto">
      <Notifications />
      <App />
    </MantineProvider>
  </React.StrictMode>,
);
```

Create `project/ts/apps/admin/src/App.tsx`:

```tsx
import { Container, Title, Text, Stack } from "@mantine/core";

export function App() {
  return (
    <Container size="sm" mt="xl">
      <Stack>
        <Title order={1}>olik admin</Title>
        <Text c="dimmed">
          Plan 10 scaffold. Resources wire up in subsequent tasks.
        </Text>
      </Stack>
    </Container>
  );
}
```

- [ ] **Step 6: Install workspace deps**

Run: `cd project/ts && pnpm install 2>&1 | tail -10`
Expected: new admin app recognized, its deps resolve, no peer-dep errors.

- [ ] **Step 7: Start the dev server once to smoke-check**

Run: `cd project/ts/apps/admin && timeout 12 pnpm dev 2>&1 | tail -12`
Expected: Vite reports `Local:   http://localhost:5174/` within ~3 seconds; the timeout kills it after 12s without error. A HEAD request against the server (via `curl -sI http://localhost:5174/` issued during a manual smoke) would return `200 OK` — we don't assert that in CI, just that `pnpm dev` boots without throwing.

- [ ] **Step 8: Typecheck and build**

Run: `cd project/ts/apps/admin && pnpm typecheck 2>&1 | tail -5`
Expected: no errors.

Run: `cd project/ts/apps/admin && pnpm build 2>&1 | tail -5`
Expected: Vite produces `dist/` with `index.html` and a bundled JS chunk.

- [ ] **Step 9: Commit**

```bash
git add project/ts/apps/admin/ project/ts/pnpm-lock.yaml
git commit -m "feat(admin): scaffold empty Refine + Mantine 9 shell on port 5174"
```

---

## Task 6: Refine data provider + auth-provider stub

**Files:**
- Create: `project/ts/apps/admin/src/data-provider.ts`
- Create: `project/ts/apps/admin/src/auth-provider.ts`
- Modify: `project/ts/apps/admin/src/App.tsx`
- Create: `project/ts/apps/admin/src/__tests__/data-provider.test.ts`

- [ ] **Step 1: Write the failing test**

Create `project/ts/apps/admin/src/__tests__/data-provider.test.ts`:

```ts
import { describe, it, expect, vi } from "vitest";

import { createDataProvider } from "../data-provider.js";
import type { OlikDb, GlyphSummary } from "@olik/glyph-db";

function mockDb(): OlikDb {
  return {
    listGlyphs: vi.fn(async () => ({
      items: [
        { char: "林", stroke_count: 8, radical: "木", iou_mean: 0.83 } as GlyphSummary,
      ],
    })),
    getGlyph: vi.fn(async () => ({ char: "林", status: "needs_review" } as any)),
    listPrototypes: vi.fn(async () => []),
    getPrototypeUsers: vi.fn(async () => []),
    listVariants: vi.fn(async () => []),
    subscribeVariants: vi.fn(async () => async () => {}),
    updateGlyphStatus: vi.fn(async () => {}),
    close: vi.fn(async () => {}),
  };
}

describe("createDataProvider", () => {
  it("maps getList('glyph') to db.listGlyphs with translated filters", async () => {
    const db = mockDb();
    const dp = createDataProvider(db);
    const result = await dp.getList({
      resource: "glyph",
      filters: [
        { field: "status", operator: "in", value: ["needs_review"] },
        { field: "iou_mean", operator: "between", value: [0.5, 0.9] },
      ],
      sorters: [{ field: "iou_mean", order: "desc" }],
      pagination: { currentPage: 1, pageSize: 50 },
    });
    expect(db.listGlyphs).toHaveBeenCalledWith(
      expect.objectContaining({
        filter: expect.objectContaining({
          status: ["needs_review"],
          iouRange: [0.5, 0.9],
        }),
        sort: "iou_mean",
        pageSize: 50,
      }),
    );
    expect(result.data).toHaveLength(1);
  });

  it("maps getOne('glyph', char) to db.getGlyph", async () => {
    const db = mockDb();
    const dp = createDataProvider(db);
    const result = await dp.getOne({ resource: "glyph", id: "林" });
    expect(db.getGlyph).toHaveBeenCalledWith("林");
    expect(result.data).toMatchObject({ char: "林" });
  });

  it("maps update('glyph', {status, review_note}) to db.updateGlyphStatus", async () => {
    const db = mockDb();
    const dp = createDataProvider(db);
    await dp.update({
      resource: "glyph",
      id: "林",
      variables: { status: "verified", review_note: "lgtm" },
    });
    expect(db.updateGlyphStatus).toHaveBeenCalledWith(
      "林",
      expect.objectContaining({ newStatus: "verified", reviewNote: "lgtm" }),
    );
  });

  it("returns an empty list for style_variant (Plan 11 stub)", async () => {
    const db = mockDb();
    const dp = createDataProvider(db);
    const result = await dp.getList({
      resource: "style_variant",
      pagination: { currentPage: 1, pageSize: 50 },
    });
    expect(result).toEqual({ data: [], total: 0 });
  });

  it("throws on unsupported operations", async () => {
    const db = mockDb();
    const dp = createDataProvider(db);
    await expect(
      dp.create({ resource: "glyph", variables: {} }),
    ).rejects.toThrow(/not supported/i);
    await expect(
      dp.deleteOne({ resource: "glyph", id: "林" }),
    ).rejects.toThrow(/not supported/i);
  });
});
```

- [ ] **Step 2: Run the test to confirm it fails**

Run: `cd project/ts/apps/admin && pnpm test 2>&1 | tail -20`
Expected: fails with `Cannot find module '../data-provider.js'`.

- [ ] **Step 3: Implement the data provider**

Create `project/ts/apps/admin/src/data-provider.ts`:

```ts
import type { DataProvider, CrudFilter, CrudSort } from "@refinedev/core";
import type {
  OlikDb,
  GlyphSummary,
  ListFilter,
  Status,
} from "@olik/glyph-db";

type Resource = "glyph" | "style_variant";

function mapFilters(filters: CrudFilter[] | undefined): ListFilter {
  const out: ListFilter = {};
  for (const f of filters ?? []) {
    if (!("field" in f)) continue;
    switch (f.field) {
      case "status":
        if (f.operator === "eq" || f.operator === "in") {
          out.status = Array.isArray(f.value) ? (f.value as Status[]) : (f.value as Status);
        }
        break;
      case "iou_mean":
        if (f.operator === "between" && Array.isArray(f.value)) {
          out.iouRange = [Number(f.value[0]), Number(f.value[1])];
        } else if (f.operator === "lt") {
          out.iouBelow = Number(f.value);
        }
        break;
      case "stroke_count":
        if (f.operator === "between" && Array.isArray(f.value)) {
          out.strokeCountRange = [Number(f.value[0]), Number(f.value[1])];
        }
        break;
      case "radical":
        if (f.operator === "eq") {
          out.radical = String(f.value);
        }
        break;
      default:
        if (typeof console !== "undefined") {
          console.warn("data-provider: unsupported filter", f);
        }
    }
  }
  return out;
}

function mapSort(sorters: CrudSort[] | undefined): "char" | "stroke_count" | "iou_mean" {
  const s = sorters?.[0];
  if (s?.field === "stroke_count") return "stroke_count";
  if (s?.field === "iou_mean") return "iou_mean";
  return "char";
}

export function createDataProvider(db: OlikDb): DataProvider {
  const notSupported = (op: string) =>
    Promise.reject(new Error(`${op} is not supported in Plan 10`));

  return {
    getList: async ({ resource, filters, sorters, pagination }) => {
      if (resource === "style_variant") {
        return { data: [], total: 0 };
      }
      if (resource !== "glyph") {
        throw new Error(`unknown resource: ${resource}`);
      }
      const page = await db.listGlyphs({
        filter: mapFilters(filters),
        sort: mapSort(sorters),
        pageSize: pagination?.pageSize ?? 50,
      });
      return { data: page.items as unknown as GlyphSummary[], total: page.items.length };
    },
    getOne: async ({ resource, id }) => {
      if (resource !== "glyph") throw new Error(`getOne only supported for glyph`);
      const row = await db.getGlyph(String(id));
      if (row === null) throw new Error(`glyph not found: ${id}`);
      return { data: { ...row, id: row.char } as any };
    },
    update: async ({ resource, id, variables }) => {
      if (resource !== "glyph") throw new Error(`update only supported for glyph`);
      const v = variables as { status?: Status; review_note?: string | null };
      if (!v.status) throw new Error("update requires { status }");
      await db.updateGlyphStatus(String(id), {
        newStatus: v.status,
        reviewNote: v.review_note ?? null,
        reviewedBy: currentUser(),
      });
      const row = await db.getGlyph(String(id));
      return { data: { ...row, id: String(id) } as any };
    },
    create: () => notSupported("create"),
    deleteOne: () => notSupported("deleteOne"),
    updateMany: () => notSupported("updateMany"),
    custom: () => notSupported("custom"),
    getApiUrl: () => "olik://surrealdb",
    getMany: async ({ resource, ids }) => {
      if (resource !== "glyph") throw new Error("getMany only supported for glyph");
      const rows = await Promise.all(ids.map((id) => db.getGlyph(String(id))));
      return { data: rows.filter((r) => r !== null).map((r) => ({ ...r, id: r!.char })) as any[] };
    },
  } as DataProvider;
}

function currentUser(): string {
  const env = (import.meta as ImportMeta & { env?: { VITE_REVIEWER?: string } }).env;
  return env?.VITE_REVIEWER ?? "browser";
}
```

Create `project/ts/apps/admin/src/auth-provider.ts`:

```ts
import type { AuthProvider } from "@refinedev/core";

/**
 * Solo-dev local posture: no authentication, no permission checks.
 * Plan 11+ can introduce a real auth provider if multi-user is added.
 */
export const noopAuthProvider: AuthProvider = {
  login: async () => ({ success: true }),
  logout: async () => ({ success: true }),
  check: async () => ({ authenticated: true }),
  onError: async () => ({}),
  getPermissions: async () => [],
  getIdentity: async () => ({ id: "local", name: "reviewer" }),
};
```

- [ ] **Step 4: Wire the provider into App.tsx (leave Refine router empty until Task 7)**

Replace `project/ts/apps/admin/src/App.tsx` with:

```tsx
import { useEffect, useState } from "react";
import { Container, Title, Text, Stack, Loader, Alert } from "@mantine/core";
import { Refine } from "@refinedev/core";
import { createDb, type OlikDb } from "@olik/glyph-db";

import { createDataProvider } from "./data-provider.js";
import { noopAuthProvider } from "./auth-provider.js";

export function App() {
  const [db, setDb] = useState<OlikDb | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    createDb()
      .then((instance) => {
        if (!cancelled) setDb(instance);
      })
      .catch((e) => {
        if (!cancelled) setError(String(e));
      });
    return () => {
      cancelled = true;
      db?.close();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (error) {
    return (
      <Container size="sm" mt="xl">
        <Alert color="red" title="SurrealDB connection failed">
          {error}
        </Alert>
      </Container>
    );
  }
  if (db === null) {
    return (
      <Container size="sm" mt="xl">
        <Loader />
      </Container>
    );
  }

  return (
    <Refine
      dataProvider={createDataProvider(db)}
      authProvider={noopAuthProvider}
      resources={[
        { name: "glyph" },
        { name: "style_variant" },
      ]}
    >
      <Container size="sm" mt="xl">
        <Stack>
          <Title order={1}>olik admin</Title>
          <Text c="dimmed">Refine is wired. Resources land in Task 7.</Text>
        </Stack>
      </Container>
    </Refine>
  );
}
```

- [ ] **Step 5: Run tests and typecheck**

Run: `cd project/ts/apps/admin && pnpm test 2>&1 | tail -10`
Expected: 5 tests pass.

Run: `cd project/ts/apps/admin && pnpm typecheck 2>&1 | tail -5`
Expected: no errors.

- [ ] **Step 6: Commit**

```bash
git add project/ts/apps/admin/
git commit -m "feat(admin): Refine data provider over @olik/glyph-db + no-op auth"
```

---

## Task 7: Glyph list resource (Mantine Table + filters + virtualization)

**Files:**
- Create: `project/ts/apps/admin/src/resources/glyph/list.tsx`
- Create: `project/ts/apps/admin/src/components/GlyphThumb.tsx`
- Modify: `project/ts/apps/admin/src/App.tsx`
- Create: `project/ts/apps/admin/src/__tests__/glyph-list.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `project/ts/apps/admin/src/__tests__/glyph-list.test.tsx`:

```tsx
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { MantineProvider } from "@mantine/core";
import { Refine } from "@refinedev/core";

import { createDataProvider } from "../data-provider.js";
import { GlyphList } from "../resources/glyph/list.js";

function renderWithProviders(db: ReturnType<typeof mockDb>) {
  return render(
    <MantineProvider>
      <Refine dataProvider={createDataProvider(db)} resources={[{ name: "glyph" }]}>
        <GlyphList />
      </Refine>
    </MantineProvider>,
  );
}

function mockDb() {
  return {
    listGlyphs: vi.fn(async ({ filter }: { filter?: { status?: unknown } }) => ({
      items: [
        { char: "林", stroke_count: 8, radical: "木", iou_mean: 0.83 },
        { char: "森", stroke_count: 12, radical: "木", iou_mean: 0.95 },
      ],
      _filter: filter,
    })),
    getGlyph: vi.fn(async () => null),
    listPrototypes: vi.fn(async () => []),
    getPrototypeUsers: vi.fn(async () => []),
    listVariants: vi.fn(async () => []),
    subscribeVariants: vi.fn(async () => async () => {}),
    updateGlyphStatus: vi.fn(async () => {}),
    close: vi.fn(async () => {}),
  } as unknown as Parameters<typeof createDataProvider>[0];
}

describe("GlyphList", () => {
  it("defaults the status filter to needs_review on first render", async () => {
    const db = mockDb();
    renderWithProviders(db);
    await screen.findByText("林");
    const lastCallArgs = (db.listGlyphs as ReturnType<typeof vi.fn>).mock.calls[0][0];
    expect(lastCallArgs.filter.status).toEqual(["needs_review"]);
  });

  it("renders one row per glyph with char + iou_mean visible", async () => {
    const db = mockDb();
    renderWithProviders(db);
    expect(await screen.findByText("林")).toBeTruthy();
    expect(await screen.findByText("森")).toBeTruthy();
    expect(screen.getByText("0.830")).toBeTruthy();
    expect(screen.getByText("0.950")).toBeTruthy();
  });

  it("allows toggling the status filter via the multi-select", async () => {
    const db = mockDb();
    renderWithProviders(db);
    await screen.findByText("林");
    const multiselect = screen.getByLabelText("Status filter");
    fireEvent.click(multiselect);
    // Mantine MultiSelect options render in a portal; we assert the
    // underlying listGlyphs was called and will assert filter shape on
    // the second call once an option is chosen. This smoke just
    // asserts the widget exists and is interactive.
    expect(multiselect).toBeTruthy();
  });
});
```

- [ ] **Step 2: Run the test to confirm it fails**

Run: `cd project/ts/apps/admin && pnpm test -- --run glyph-list.test 2>&1 | tail -15`
Expected: fails with "Cannot find module '../resources/glyph/list.js'".

- [ ] **Step 3: Implement GlyphThumb component**

Create `project/ts/apps/admin/src/components/GlyphThumb.tsx`:

```tsx
import { memo } from "react";

interface GlyphThumbProps {
  char: string;
  size?: number;
}

/**
 * Simple char thumbnail. Plan 10 uses the system CJK font as a proxy
 * for the composed shape — the list grid is a pick-from-queue surface,
 * not a final-output preview. The detail view renders the real
 * composed SVG (Task 9).
 */
export const GlyphThumb = memo(function GlyphThumb({ char, size = 36 }: GlyphThumbProps) {
  return (
    <span
      style={{
        display: "inline-block",
        width: size,
        height: size,
        fontSize: size * 0.85,
        lineHeight: `${size}px`,
        textAlign: "center",
        fontFamily: "system-ui, 'Noto Sans CJK TC', sans-serif",
      }}
    >
      {char}
    </span>
  );
});
```

- [ ] **Step 4: Implement GlyphList**

Create `project/ts/apps/admin/src/resources/glyph/list.tsx`:

```tsx
import { useMemo, useState } from "react";
import { Link } from "react-router";
import {
  Badge,
  Group,
  MultiSelect,
  Paper,
  RangeSlider,
  Stack,
  Table,
  Text,
  TextInput,
  Title,
} from "@mantine/core";
import { useList } from "@refinedev/core";
import type { Status } from "@olik/glyph-db";
import { STATUS_VALUES } from "@olik/glyph-db";

import { GlyphThumb } from "../../components/GlyphThumb.js";

const STATUS_COLOR: Record<Status, string> = {
  verified: "green",
  needs_review: "yellow",
  unsupported_op: "gray",
  failed_extraction: "red",
};

export function GlyphList() {
  const [statuses, setStatuses] = useState<Status[]>(["needs_review"]);
  const [iouRange, setIouRange] = useState<[number, number]>([0, 1]);
  const [strokeRange, setStrokeRange] = useState<[number, number]>([1, 30]);
  const [radical, setRadical] = useState("");

  const filters = useMemo(() => {
    const out: Parameters<typeof useList>[0]["filters"] = [
      { field: "status", operator: "in", value: statuses },
      { field: "iou_mean", operator: "between", value: iouRange },
      { field: "stroke_count", operator: "between", value: strokeRange },
    ];
    if (radical.trim().length > 0) {
      out.push({ field: "radical", operator: "eq", value: radical.trim() });
    }
    return out;
  }, [statuses, iouRange, strokeRange, radical]);

  const { data, isLoading } = useList({
    resource: "glyph",
    filters,
    sorters: [{ field: "iou_mean", order: "desc" }],
    pagination: { pageSize: 200 },
  });

  const rows = data?.data ?? [];

  return (
    <Stack p="md">
      <Title order={2}>Review queue</Title>
      <Paper shadow="xs" p="md" withBorder>
        <Group align="end" wrap="wrap">
          <MultiSelect
            label="Status filter"
            aria-label="Status filter"
            data={[...STATUS_VALUES] as string[]}
            value={statuses}
            onChange={(v) => setStatuses(v as Status[])}
            w={260}
          />
          <Stack gap={2}>
            <Text size="sm">IoU range ({iouRange[0].toFixed(2)}–{iouRange[1].toFixed(2)})</Text>
            <RangeSlider
              min={0}
              max={1}
              step={0.05}
              value={iouRange}
              onChange={(v) => setIouRange(v)}
              w={240}
            />
          </Stack>
          <Stack gap={2}>
            <Text size="sm">Stroke count ({strokeRange[0]}–{strokeRange[1]})</Text>
            <RangeSlider
              min={1}
              max={30}
              step={1}
              value={strokeRange}
              onChange={(v) => setStrokeRange(v)}
              w={220}
            />
          </Stack>
          <TextInput
            label="Radical"
            value={radical}
            onChange={(e) => setRadical(e.currentTarget.value)}
            placeholder="e.g. 木"
            w={140}
          />
        </Group>
      </Paper>

      <Paper shadow="xs" withBorder>
        <Table striped highlightOnHover stickyHeader>
          <Table.Thead>
            <Table.Tr>
              <Table.Th w={80}>Char</Table.Th>
              <Table.Th w={130}>Status</Table.Th>
              <Table.Th w={100}>IoU</Table.Th>
              <Table.Th w={100}>Strokes</Table.Th>
              <Table.Th w={100}>Radical</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {isLoading && (
              <Table.Tr>
                <Table.Td colSpan={5}>Loading…</Table.Td>
              </Table.Tr>
            )}
            {rows.map((row) => {
              const r = row as unknown as {
                char: string;
                stroke_count: number;
                radical: string | null;
                iou_mean: number;
                status?: Status;
              };
              return (
                <Table.Tr key={r.char}>
                  <Table.Td>
                    <Group gap={6}>
                      <GlyphThumb char={r.char} size={28} />
                      <Link to={`/glyph/${encodeURIComponent(r.char)}`}>{r.char}</Link>
                    </Group>
                  </Table.Td>
                  <Table.Td>
                    <Badge color={STATUS_COLOR[r.status ?? "needs_review"]} variant="light">
                      {r.status ?? "needs_review"}
                    </Badge>
                  </Table.Td>
                  <Table.Td>{r.iou_mean.toFixed(3)}</Table.Td>
                  <Table.Td>{r.stroke_count}</Table.Td>
                  <Table.Td>{r.radical ?? "—"}</Table.Td>
                </Table.Tr>
              );
            })}
            {!isLoading && rows.length === 0 && (
              <Table.Tr>
                <Table.Td colSpan={5}>No rows match the current filter.</Table.Td>
              </Table.Tr>
            )}
          </Table.Tbody>
        </Table>
      </Paper>
    </Stack>
  );
}
```

- [ ] **Step 5: Wire the list into App.tsx with routing**

Edit `project/ts/apps/admin/src/App.tsx`. Replace its body with:

```tsx
import { useEffect, useState } from "react";
import { Alert, Container, Loader } from "@mantine/core";
import { Refine } from "@refinedev/core";
import routerBindings from "@refinedev/react-router";
import { BrowserRouter, Navigate, Route, Routes } from "react-router";
import { createDb, type OlikDb } from "@olik/glyph-db";

import { createDataProvider } from "./data-provider.js";
import { noopAuthProvider } from "./auth-provider.js";
import { GlyphList } from "./resources/glyph/list.js";

export function App() {
  const [db, setDb] = useState<OlikDb | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    createDb()
      .then((instance) => {
        if (!cancelled) setDb(instance);
      })
      .catch((e) => {
        if (!cancelled) setError(String(e));
      });
    return () => {
      cancelled = true;
      db?.close();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (error) {
    return (
      <Container size="sm" mt="xl">
        <Alert color="red" title="SurrealDB connection failed">
          {error}
        </Alert>
      </Container>
    );
  }
  if (db === null) {
    return (
      <Container size="sm" mt="xl">
        <Loader />
      </Container>
    );
  }

  return (
    <BrowserRouter>
      <Refine
        dataProvider={createDataProvider(db)}
        authProvider={noopAuthProvider}
        routerProvider={routerBindings}
        resources={[
          { name: "glyph", list: "/glyph", show: "/glyph/:id" },
          { name: "style_variant", list: "/style_variant" },
        ]}
      >
        <Routes>
          <Route path="/" element={<Navigate to="/glyph" replace />} />
          <Route path="/glyph" element={<GlyphList />} />
          {/* Detail route arrives in Task 9 */}
        </Routes>
      </Refine>
    </BrowserRouter>
  );
}
```

- [ ] **Step 6: Run tests and typecheck**

Run: `cd project/ts/apps/admin && pnpm test 2>&1 | tail -15`
Expected: glyph-list tests pass; data-provider tests still green.

Run: `cd project/ts/apps/admin && pnpm typecheck 2>&1 | tail -5`
Expected: no errors.

- [ ] **Step 7: Commit**

```bash
git add project/ts/apps/admin/
git commit -m "feat(admin): glyph list with status/iou/stroke_count/radical filters"
```

---

## Task 8: SVG components — GlyphSvg + MmhSvg

**Files:**
- Create: `project/ts/apps/admin/src/components/GlyphSvg.tsx`
- Create: `project/ts/apps/admin/src/components/MmhSvg.tsx`

Simple, shared stroke-path renderers. Both apply the canonical y-up to y-down flip at render time (`translate(0, h) scale(1, -1)` per the Plan 09.1 convention).

- [ ] **Step 1: Implement GlyphSvg**

Create `project/ts/apps/admin/src/components/GlyphSvg.tsx`:

```tsx
import { memo } from "react";

interface GlyphSvgProps {
  /** Path-d strings from glyph.stroke_instances (composed output). */
  strokes: readonly string[];
  /** SVG viewbox square side length in canonical units (default 1024). */
  canvas?: number;
  /** Rendered size in CSS pixels. */
  size?: number;
  /** CSS background color for contrast. */
  background?: string;
}

/**
 * Renders composed stroke paths with the y-up to y-down flip applied
 * at the group level, matching preview-glyph.py and the existing
 * quickview renderer.
 */
export const GlyphSvg = memo(function GlyphSvg({
  strokes,
  canvas = 1024,
  size = 512,
  background = "#ffffff",
}: GlyphSvgProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox={`0 0 ${canvas} ${canvas}`}
      style={{ background, display: "block" }}
    >
      <g transform={`translate(0, ${canvas}) scale(1, -1)`}>
        {strokes.map((d, i) => (
          <path key={i} d={d} fill="#0f172a" stroke="none" />
        ))}
      </g>
    </svg>
  );
});
```

- [ ] **Step 2: Implement MmhSvg**

Create `project/ts/apps/admin/src/components/MmhSvg.tsx`:

```tsx
import { memo } from "react";

interface MmhSvgProps {
  /** MMH stroke path-d strings from glyph.mmh_strokes. */
  strokes: readonly string[];
  canvas?: number;
  size?: number;
  background?: string;
}

/**
 * Renders the MMH reference strokes. Shares the same coord space and
 * flip as GlyphSvg so the two panels are visually comparable — any
 * structural difference indicates a real extraction issue rather than
 * a coordinate-frame mismatch.
 */
export const MmhSvg = memo(function MmhSvg({
  strokes,
  canvas = 1024,
  size = 512,
  background = "#f8fafc",
}: MmhSvgProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox={`0 0 ${canvas} ${canvas}`}
      style={{ background, display: "block" }}
    >
      <g transform={`translate(0, ${canvas}) scale(1, -1)`}>
        {strokes.map((d, i) => (
          <path key={i} d={d} fill="#334155" stroke="none" />
        ))}
      </g>
    </svg>
  );
});
```

- [ ] **Step 3: Typecheck**

Run: `cd project/ts/apps/admin && pnpm typecheck 2>&1 | tail -5`
Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add project/ts/apps/admin/src/components/GlyphSvg.tsx \
        project/ts/apps/admin/src/components/MmhSvg.tsx
git commit -m "feat(admin): GlyphSvg + MmhSvg renderers with y-up flip"
```

---

## Task 9: Glyph detail view — split panel, keyboard shortcuts, approve/reject

**Files:**
- Create: `project/ts/apps/admin/src/resources/glyph/detail.tsx`
- Create: `project/ts/apps/admin/src/components/ReviewActions.tsx`
- Modify: `project/ts/apps/admin/src/App.tsx` — add `/glyph/:id` route
- Create: `project/ts/apps/admin/src/__tests__/review-actions.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `project/ts/apps/admin/src/__tests__/review-actions.test.tsx`:

```tsx
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { MantineProvider } from "@mantine/core";

import { ReviewActions } from "../components/ReviewActions.js";

describe("ReviewActions", () => {
  it("calls onApprove when Y is pressed", () => {
    const onApprove = vi.fn();
    const onReject = vi.fn();
    render(
      <MantineProvider>
        <ReviewActions
          currentStatus="needs_review"
          reviewNote=""
          onNoteChange={() => {}}
          onApprove={onApprove}
          onReject={onReject}
          onNext={() => {}}
          onPrev={() => {}}
        />
      </MantineProvider>,
    );
    fireEvent.keyDown(window, { key: "y" });
    expect(onApprove).toHaveBeenCalledOnce();
    expect(onReject).not.toHaveBeenCalled();
  });

  it("calls onReject when N is pressed, passing the current review note", () => {
    const onReject = vi.fn();
    const { rerender } = render(
      <MantineProvider>
        <ReviewActions
          currentStatus="needs_review"
          reviewNote="bad placement"
          onNoteChange={() => {}}
          onApprove={() => {}}
          onReject={onReject}
          onNext={() => {}}
          onPrev={() => {}}
        />
      </MantineProvider>,
    );
    fireEvent.keyDown(window, { key: "n" });
    expect(onReject).toHaveBeenCalledWith("bad placement");
    rerender(<></>);
  });

  it("calls onNext/onPrev when J/K are pressed", () => {
    const onNext = vi.fn();
    const onPrev = vi.fn();
    render(
      <MantineProvider>
        <ReviewActions
          currentStatus="needs_review"
          reviewNote=""
          onNoteChange={() => {}}
          onApprove={() => {}}
          onReject={() => {}}
          onNext={onNext}
          onPrev={onPrev}
        />
      </MantineProvider>,
    );
    fireEvent.keyDown(window, { key: "j" });
    fireEvent.keyDown(window, { key: "k" });
    expect(onNext).toHaveBeenCalledOnce();
    expect(onPrev).toHaveBeenCalledOnce();
  });

  it("disables Approve for rows already verified (no self-transition keystroke)", () => {
    const onApprove = vi.fn();
    render(
      <MantineProvider>
        <ReviewActions
          currentStatus="verified"
          reviewNote=""
          onNoteChange={() => {}}
          onApprove={onApprove}
          onReject={() => {}}
          onNext={() => {}}
          onPrev={() => {}}
        />
      </MantineProvider>,
    );
    fireEvent.keyDown(window, { key: "y" });
    expect(onApprove).not.toHaveBeenCalled();
    expect(screen.getByText(/Already verified/i)).toBeTruthy();
  });
});
```

- [ ] **Step 2: Run the test to confirm it fails**

Run: `cd project/ts/apps/admin && pnpm test -- --run review-actions 2>&1 | tail -15`
Expected: fails on import error.

- [ ] **Step 3: Implement ReviewActions**

Create `project/ts/apps/admin/src/components/ReviewActions.tsx`:

```tsx
import { Button, Group, Stack, Text, Textarea } from "@mantine/core";
import { useHotkeys } from "@mantine/hooks";
import type { Status } from "@olik/glyph-db";

interface ReviewActionsProps {
  currentStatus: Status;
  reviewNote: string;
  onNoteChange: (note: string) => void;
  onApprove: () => void;
  onReject: (note: string) => void;
  onNext: () => void;
  onPrev: () => void;
}

export function ReviewActions({
  currentStatus,
  reviewNote,
  onNoteChange,
  onApprove,
  onReject,
  onNext,
  onPrev,
}: ReviewActionsProps) {
  const alreadyVerified = currentStatus === "verified";
  const alreadyRejected = currentStatus === "failed_extraction";

  useHotkeys([
    ["y", () => { if (!alreadyVerified) onApprove(); }],
    ["n", () => { if (!alreadyRejected) onReject(reviewNote); }],
    ["j", () => onNext()],
    ["k", () => onPrev()],
    ["r", () => document.getElementById("review-note")?.focus()],
  ]);

  return (
    <Stack>
      <Textarea
        id="review-note"
        label="Review note (optional)"
        placeholder="e.g. top component placement off by ~10 units"
        value={reviewNote}
        onChange={(e) => onNoteChange(e.currentTarget.value)}
        autosize
        minRows={2}
      />
      <Group>
        <Button
          color="green"
          onClick={() => onApprove()}
          disabled={alreadyVerified}
        >
          {alreadyVerified ? "Already verified" : "Approve (Y)"}
        </Button>
        <Button
          color="red"
          variant="outline"
          onClick={() => onReject(reviewNote)}
          disabled={alreadyRejected}
        >
          {alreadyRejected ? "Already rejected" : "Reject (N)"}
        </Button>
        <Button variant="subtle" onClick={onPrev}>Prev (K)</Button>
        <Button variant="subtle" onClick={onNext}>Next (J)</Button>
      </Group>
      <Text size="xs" c="dimmed">
        Shortcuts: Y approve · N reject · J next · K prev · R focus note · Esc back
      </Text>
    </Stack>
  );
}
```

- [ ] **Step 4: Implement GlyphDetail**

Create `project/ts/apps/admin/src/resources/glyph/detail.tsx`:

```tsx
import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router";
import {
  Alert,
  Badge,
  Button,
  Grid,
  Group,
  Loader,
  Paper,
  Stack,
  Text,
  Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useHotkeys } from "@mantine/hooks";
import { useList, useOne, useUpdate } from "@refinedev/core";
import type { Status } from "@olik/glyph-db";

import { GlyphSvg } from "../../components/GlyphSvg.js";
import { MmhSvg } from "../../components/MmhSvg.js";
import { ReviewActions } from "../../components/ReviewActions.js";

export function GlyphDetail() {
  const { id } = useParams<{ id: string }>();
  const char = id ? decodeURIComponent(id) : "";
  const navigate = useNavigate();

  const { data: one, isLoading } = useOne({ resource: "glyph", id: char });
  const { data: list } = useList({
    resource: "glyph",
    filters: [{ field: "status", operator: "in", value: ["needs_review"] }],
    sorters: [{ field: "iou_mean", order: "desc" }],
    pagination: { pageSize: 500 },
  });
  const { mutate: updateGlyph, isLoading: updating } = useUpdate();

  const [reviewNote, setReviewNote] = useState("");
  useEffect(() => {
    const existing = (one?.data as { review_note?: string } | undefined)?.review_note;
    setReviewNote(existing ?? "");
  }, [one?.data]);

  const queue: string[] = ((list?.data as Array<{ char: string }>) ?? []).map((r) => r.char);
  const idx = queue.indexOf(char);

  const goTo = useCallback(
    (nextIdx: number) => {
      const target = queue[nextIdx];
      if (target !== undefined) navigate(`/glyph/${encodeURIComponent(target)}`);
    },
    [queue, navigate],
  );

  const transition = useCallback(
    (newStatus: Status, note: string | null) => {
      updateGlyph(
        {
          resource: "glyph",
          id: char,
          values: { status: newStatus, review_note: note },
        },
        {
          onSuccess: () => {
            notifications.show({
              color: newStatus === "verified" ? "green" : "red",
              message: `${char} → ${newStatus}`,
            });
            if (idx >= 0) goTo(idx + 1);
          },
          onError: (e) =>
            notifications.show({
              color: "red",
              title: "Update failed",
              message: String(e),
            }),
        },
      );
    },
    [char, idx, updateGlyph, goTo],
  );

  useHotkeys([
    ["escape", () => navigate("/glyph")],
  ]);

  if (isLoading || one?.data === undefined) {
    return (
      <Stack p="md">
        <Loader />
      </Stack>
    );
  }

  const row = one.data as unknown as {
    char: string;
    status: Status;
    iou_mean?: number;
    stroke_count?: number;
    radical?: string | null;
    stroke_instances?: Array<{ d?: string }>;
    mmh_strokes?: string[];
    components?: unknown[];
    extraction_run?: string;
    reviewed_at?: string;
    reviewed_by?: string;
  };

  const composedPaths = (row.stroke_instances ?? [])
    .map((s) => s.d ?? "")
    .filter((d) => d.length > 0);
  const mmhPaths = row.mmh_strokes ?? [];

  if (mmhPaths.length === 0) {
    return (
      <Stack p="md">
        <Alert color="yellow" title="No MMH reference">
          This glyph row lacks <code>mmh_strokes</code> — pre-Plan-10 row.
          Re-run <code>olik extract retry</code> to backfill.
        </Alert>
        <Button component={Link} to="/glyph" variant="subtle">Back</Button>
      </Stack>
    );
  }

  return (
    <Stack p="md">
      <Group justify="space-between">
        <Group>
          <Title order={2}>{row.char}</Title>
          <Badge color={row.status === "verified" ? "green" : row.status === "failed_extraction" ? "red" : "yellow"}>
            {row.status}
          </Badge>
          <Text c="dimmed">iou={row.iou_mean?.toFixed(3) ?? "—"}</Text>
          {idx >= 0 && <Text c="dimmed">{idx + 1}/{queue.length}</Text>}
        </Group>
        <Button component={Link} to="/glyph" variant="subtle">Back (Esc)</Button>
      </Group>

      <Grid>
        <Grid.Col span={6}>
          <Paper shadow="xs" withBorder>
            <Stack p="xs">
              <Text size="sm" c="dimmed">Composed</Text>
              <GlyphSvg strokes={composedPaths} size={480} />
            </Stack>
          </Paper>
        </Grid.Col>
        <Grid.Col span={6}>
          <Paper shadow="xs" withBorder>
            <Stack p="xs">
              <Text size="sm" c="dimmed">MMH reference</Text>
              <MmhSvg strokes={mmhPaths} size={480} />
            </Stack>
          </Paper>
        </Grid.Col>
      </Grid>

      <Paper shadow="xs" p="md" withBorder>
        <Stack gap={4}>
          <Text size="sm">strokes: {row.stroke_count ?? composedPaths.length} · radical: {row.radical ?? "—"}</Text>
          <Text size="sm">extraction_run: {row.extraction_run ?? "—"}</Text>
          {row.reviewed_at && (
            <Text size="sm" c="dimmed">
              reviewed {row.reviewed_at} by {row.reviewed_by ?? "?"}
            </Text>
          )}
        </Stack>
      </Paper>

      <ReviewActions
        currentStatus={row.status}
        reviewNote={reviewNote}
        onNoteChange={setReviewNote}
        onApprove={() => transition("verified", reviewNote || null)}
        onReject={(note) => transition("failed_extraction", note || null)}
        onNext={() => goTo(idx + 1)}
        onPrev={() => goTo(idx - 1)}
      />

      {updating && <Text size="xs" c="dimmed">Saving…</Text>}
    </Stack>
  );
}
```

- [ ] **Step 5: Wire the detail route in App.tsx**

Edit `project/ts/apps/admin/src/App.tsx`. Add the import:

```tsx
import { GlyphDetail } from "./resources/glyph/detail.js";
```

And in the `<Routes>` block, add:

```tsx
<Route path="/glyph/:id" element={<GlyphDetail />} />
```

After the existing `/glyph` route.

- [ ] **Step 6: Run tests and typecheck**

Run: `cd project/ts/apps/admin && pnpm test 2>&1 | tail -10`
Expected: all tests pass (data-provider + glyph-list + review-actions).

Run: `cd project/ts/apps/admin && pnpm typecheck 2>&1 | tail -5`
Expected: no errors.

- [ ] **Step 7: Commit**

```bash
git add project/ts/apps/admin/
git commit -m "feat(admin): glyph detail view with split panel + keyboard review"
```

---

## Task 10: Style_variant stub + end-to-end smoke + Plan 10 tag

**Files:**
- Create: `project/ts/apps/admin/src/resources/style_variant/list.tsx`
- Modify: `project/ts/apps/admin/src/App.tsx` — add `/style_variant` route

- [ ] **Step 1: Implement the stub**

Create `project/ts/apps/admin/src/resources/style_variant/list.tsx`:

```tsx
import { Alert, Container, Stack, Title } from "@mantine/core";

export function StyleVariantList() {
  return (
    <Container size="md" mt="xl">
      <Stack>
        <Title order={2}>Style variants</Title>
        <Alert color="blue" title="Reserved for Plan 11">
          ComfyUI-generated style variants will appear here once Plan 11 lands.
          Plan 10 ships this route as a placeholder so the Refine resource
          declaration is non-empty.
        </Alert>
      </Stack>
    </Container>
  );
}
```

- [ ] **Step 2: Wire the route**

Edit `project/ts/apps/admin/src/App.tsx`. Add import:

```tsx
import { StyleVariantList } from "./resources/style_variant/list.js";
```

Add inside `<Routes>`:

```tsx
<Route path="/style_variant" element={<StyleVariantList />} />
```

- [ ] **Step 3: Final workspace-wide verification**

Run in order:

```bash
cd project/py && .venv/bin/pytest -q 2>&1 | tail -5
cd project/ts && pnpm -r test 2>&1 | tail -15
cd project/ts && pnpm -r typecheck 2>&1 | tail -10
cd project/ts && pnpm -r --filter '!@olik/remotion-studio' build 2>&1 | tail -10
```

Expected for each:
- py: 164 passed, 1 xfailed.
- ts test: glyph-db + admin test suites all green; inspector/quickview regression-green.
- typecheck: no errors across all packages.
- build: admin produces `dist/`, glyph-db produces `dist/`, other packages unchanged.

- [ ] **Step 4: Apply the Plan 10 tag and commit**

```bash
git add project/ts/apps/admin/
git commit -m "feat(admin): style_variant stub route (Plan 11 reservation)"
git tag plan-10-admin-review-ui
```

- [ ] **Step 5: Manual e2e smoke (reviewer sign-off step — not executed by the loop)**

The Archon loop stops here. A reviewer runs these before merging the PR:

```bash
cd /Users/apprenticegc/Work/lunar-horse/plate-projects/olik-font
task db:up
# Optional: task db:reset + seed if host DB state is stale
project/py/.venv/bin/olik extract auto --count 20 --seed 7
cd project/ts && pnpm install
cd project/ts/apps/admin && pnpm dev
# Browser: http://localhost:5174/
# 1. Confirm glyph list shows ~20 needs_review rows.
# 2. Click one → detail view.
# 3. Verify composed SVG + MMH reference render side-by-side.
# 4. Press Y → status becomes verified, next row auto-loads.
# 5. Press N with a review note → status becomes failed_extraction.
# 6. Reload → the two reviewed rows persist their new status.
```

Any divergence here should be captured as a follow-up issue, not a
blocker for merge — the tag + PR represent "code complete," and this
smoke is how the reviewer signs off.

---

## Self-review

1. **Spec coverage:**
   - §2 Goals → admin app scaffold (Task 5), Refine + Mantine (Task 5/6/7), List view + filters + virtualization (Task 7), Detail view + keyboard (Task 9), Status/iouRange/updateGlyphStatus (Tasks 2–3), mmh_strokes (Task 4), style_variant stub (Task 10).
   - §3 Non-goals → not implemented, confirmed by task scope.
   - §4 Architecture → Task 5 scaffolds exact dirs; Task 6 wires data provider; Task 7/9 implement resources.
   - §5 React 19 upgrade → Task 1.
   - §6 Reviewer workflow → Task 9 keyboard + state machine; Task 7 default filter `needs_review + iou_mean desc`.
   - §7 Schema changes → **gap: spec §7 proposes DDL fields, but `sink/schema.py` defines all tables as SCHEMALESS with no per-field definitions.** The fields can flow through via MERGE without DDL changes. Noted in the Task 4 commit path; no dedicated DDL task needed. If future work wants explicit field guards, add them as a Plan 10.1 follow-up.
   - §8 @olik/glyph-db → Tasks 2–3.
   - §9 Refine DataProvider → Task 6.
   - §10 Testing → TDD across Tasks 2, 3, 6, 7, 9; Python test in Task 4.
   - §11 Risks — §5's Remotion-compatibility mitigation is embedded in Task 1 Step 3; §11's "Existing SVG renderers" resolved by creating app-local copies (Task 8), not factoring into a shared package, to avoid scope creep.
   - §12 Out of scope → no tasks.

2. **Placeholder scan:** no TBD/TODO/vague steps. Every code step shows complete code.

3. **Type consistency:**
   - `Status`, `ReviewUpdate`, `VALID_TRANSITIONS`, `InvalidTransition` — defined in Task 3, used identically in Tasks 6, 7, 9.
   - `ListFilter.status` / `ListFilter.iouRange` — defined Task 2, used Task 6's data-provider mapFilters (matches).
   - `updateGlyphStatus(char, ReviewUpdate)` — signature stable across Tasks 3, 6, 9.
   - Refine hooks (`useList`, `useOne`, `useUpdate`) consistent throughout.
   - Test mocks cover all `OlikDb` methods including the new `updateGlyphStatus` — fixed during test authoring.

4. **Ambiguity check:** the "Mantine 9 not ready → fall back to Mantine 8" fallback in Task 5 Step 1 is explicit — implementation-time decision with a concrete rule.
