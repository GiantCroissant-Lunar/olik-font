---
title: "Plan 09 — Bulk extraction pipeline (design)"
created: 2026-04-21
tags: [type/spec, topic/scene-graph, topic/extraction]
status: draft
supersedes: null
relates-to:
  - "[[2026-04-21-glyph-scene-graph-solution-design]]"
  - "[[2026-04-21-03-python-compose-cli]]"
  - "[[2026-04-21-surrealdb-foundation-design]]"
---

# Plan 09 — Bulk extraction pipeline (design)

## 1. Context & motivation

Plan 08 gave us a SurrealDB-backed pipeline that ingests hand-authored glyph
records via `olik db sync <chars>`. Four seed characters live in the DB.
The project's stated scaling target is the MoE 4808 常用字 set (教育部常用字
4808 字 — Taiwan's Ministry of Education common-use list).

Hand-authoring `extraction_plan.yaml` entries for 4808 chars is infeasible —
each entry requires MMH stroke-index ranges, role tags, anchors, and
context-specific prototype variants when the canonical prototype doesn't fit
(the `proto:sheng_in_qing` pattern). We need an automated planner.

Plan 09 delivers that pipeline. The target is **500 random chars as the first
real run**, storing the full status distribution in SurrealDB. Subsequent
runs grow the filled set incrementally toward the full 4808. The "fill more
later" framing models the 4808 set as buckets, 500 of which we populate on
the first run.

## 2. Goals

- Auto-generate extraction plans in memory from `cjk-decomp.json` IDS
  decompositions + MMH stroke data.
- Support the four compose modes already implemented (`left_right`,
  `top_bottom`, `enclose`, `repeat_triangle`) plus any additional mode
  that appears in ≥ 5 % of the first random 500 (added inside Plan 09's
  scope).
- Triage each result into a four-state enum persisted on the `glyph` row:
  - `verified` — IoU ≥ gate (default 0.90); production-ready.
  - `needs_review` — IoU < gate; in DB but flagged for manual review.
  - `unsupported_op` — cjk-decomp operator not handled by the planner;
    stub row, no stroke data.
  - `failed_extraction` — MMH entry missing or corrupt; stub row.
- Prototype reuse by default with IoU-triggered context-variant fallback.
  Lineage recorded via a new `variant_of` graph edge.
- Deterministic bucket selection from `moe_4808.txt` via a `--seed` flag,
  so a workflow run is reproducible.
- Keep the existing `olik build` + `olik db sync <chars>` paths working
  for the 4 seeds + any hand-tuned chars; the new `olik extract auto`
  command is additive.
- Tests: unit coverage for the operator LUT and the reuse decision;
  an integration smoke running `--count 20` against the ephemeral
  SurrealDB fixture.

## 3. Non-goals

- No admin UI for reviewing `needs_review` entries — that's Plan 10's
  job. A CLI reviewer (`olik extract list --status needs_review`) is
  Plan 09's interim interface.
- No parallel extraction. Sequential is fast enough for 500 (seconds
  per char × 500 ≈ minutes).
- No new compose modes beyond what the random 500 surfaces with ≥ 5 %
  coverage. Edge-case operators stay in `unsupported_op` until a later
  plan adds them.
- No Plan 11 ComfyUI integration. `style_variant` + `comfyui_job` stay
  empty.
- No change to the 4 seed records' hand-authored entries in
  `extraction_plan.yaml` — they remain the canonical examples and take
  precedence over any auto-plan for those chars.

## 4. Architecture overview

```
       moe_4808.txt ───┐
                       │
  SurrealDB (filled) ──┴──► bucket_selector(seed, count)
                                 │
                                 ▼
                      cjk-decomp entry lookup
                                 │
                           ┌─────┴─────┐
                 op unsupported?       yes ──► stub row (status=unsupported_op)
                           │
                          no
                           │
                           ▼
                      auto-planner
                  (operator → compose mode,
                   component → MMH lookup)
                           │
                           ▼
                  prototype reuse/variant
                       decision loop
                           │
                           ▼
                 compose + emit (reuse
                  existing olik_font.compose)
                           │
                           ▼
                   IoU measurement
                           │
                     ≥ gate  ≥      ≥ < gate
                           │                 │
                        verified        needs_review
                           │                 │
                           └────────┬────────┘
                                    ▼
                          olik db sync (upsert +
                          variant_of edges + status)
```

Two layered decisions:

1. **Can we plan this char at all?** (Operator supported → yes/no.)
2. **Is the composed result good enough?** (IoU gate → verified vs
   needs_review.)

A char can fail either layer. Both failures land as DB rows so the whole
bucket count is accounted for.

## 5. Schema changes (additive)

### 5.1 `glyph` table — new fields

```sql
-- applied by sink/schema.py::DDL
DEFINE FIELD status           ON glyph TYPE string
  ASSERT $value IN ["verified", "needs_review", "unsupported_op", "failed_extraction"];
DEFINE FIELD missing_op       ON glyph TYPE option<string>;
DEFINE FIELD extraction_error ON glyph TYPE option<string>;
DEFINE FIELD extraction_run   ON glyph TYPE option<record<extraction_run>>;
DEFINE INDEX glyph_status     ON glyph FIELDS status;
```

SCHEMALESS on the table still applies; these DEFINE FIELD entries only
enforce type + enum where present. An empty bucket has `status = NONE`
by omission (pre-Plan-09 records are untouched).

### 5.2 New edge `variant_of`

```sql
DEFINE TABLE variant_of SCHEMALESS;
-- Auto-created by RELATE; pin for predictability.
-- Fields: reason ("iou_fallback" | "manual")
DEFINE INDEX variant_of_in_out ON variant_of FIELDS in, out UNIQUE;
```

One direction: `prototype:⟨child⟩ -> variant_of -> prototype:⟨canonical⟩`.
Example: `proto:sheng_in_qing -> variant_of -> proto:sheng`.

### 5.3 New field on `extraction_run`

```sql
DEFINE FIELD seed             ON extraction_run TYPE option<int>;
DEFINE FIELD iou_gate         ON extraction_run TYPE option<float>;
DEFINE FIELD counts           ON extraction_run TYPE option<object>;
-- counts = { verified: N, needs_review: M, unsupported_op: K, failed: J }
```

Recorded once per `olik extract auto` invocation.

## 6. CLI additions

All under a new `olik extract` subtree. Verbs:

| Command | Purpose |
|---|---|
| `olik extract auto --count N [--iou-gate 0.90] [--seed K] [--dry-run] [--max-variants-per-proto 2]` | Pick N random empty buckets, extract, upsert. |
| `olik extract retry --status {unsupported_op, needs_review, failed_extraction} [--iou-gate 0.90] [--max-variants-per-proto 2]` | Re-run extraction on already-recorded chars with the given status (useful after adding a new compose mode). |
| `olik extract report` | Print status breakdown: filled/total, per-status counts, operator histogram (including unsupported). |
| `olik extract list --status <status> [--limit N]` | Print the chars in a status bucket (reviewer interim). |
| `olik extract backfill-status` | One-shot: set `status=verified` on existing pre-Plan-09 rows (the 4 seeds) whose `iou_mean` already meets the gate. Idempotent. |

The existing `olik db sync <chars>` and `olik build` commands stay
unchanged. `olik extract auto` uses the same `_build_artifacts()` helper
under the hood but feeds it auto-planned entries rather than YAML ones.

### 6.1 `--dry-run`

Performs the full plan + compose pass but prints the intended status
distribution without writing to the DB. Used to validate a seed/count
choice before committing.

### 6.2 Reproducibility contract

`olik extract auto --count 500 --seed 42` on the same moe_4808.txt and
cjk-decomp.json commit produces an identical set of chars to select. The
resulting status distribution is also deterministic modulo MMH data drift.
The `extraction_run` row records `seed`, `iou_gate`, `olik_version`,
`mmh_commit`, `cjk_commit`, `counts`.

## 7. Python package layout

```
project/py/src/olik_font/bulk/
├── __init__.py
├── charlist.py            # load moe_4808.txt, bucket selection
├── ops.py                 # cjk-decomp op → compose mode LUT
├── planner.py             # auto-generate InstancePlan per char
├── reuse.py               # prototype reuse decision + IoU fallback
├── status.py              # Status enum + transitions
└── batch.py               # orchestrator: select → plan → extract → gate → commit
```

Supporting data:

```
project/py/data/
├── moe_4808.txt           # committed snapshot
└── LICENSE-moe-4808       # attribution + license
```

### 7.1 `charlist.py`

```python
SEED_DEFAULT = 42

def load_moe_4808() -> list[str]: ...
def select_buckets(
    all_chars: list[str],
    already_filled: set[str],
    count: int,
    seed: int,
) -> list[str]: ...
```

`select_buckets` uses `random.Random(seed)` to pick `count` chars from
`all_chars - already_filled`. Returns empty list if no buckets remain.

### 7.2 `ops.py`

```python
OP_TO_MODE: dict[str, str] = {
    "a":    "left_right",
    "d":    "top_bottom",
    "s":    "enclose",
    "r3tr": "repeat_triangle",
    # More added as random 500 surfaces demand (>= 5% coverage).
}

UNSUPPORTED_SENTINEL = None

def resolve_mode(op: str) -> str | None:
    return OP_TO_MODE.get(op)
```

### 7.3 `planner.py`

One function, given a char:

```python
def plan_char(
    char: str,
    cjk_entry: dict,     # {"operator": "a", "components": ["日", "月"]}
    mmh: dict,           # pre-loaded MMH graphics
    existing_protos: ProtoIndex,
) -> PlanResult:
    """Return a PlanResult with either an InstanceTree + list of new
    prototypes, OR a status=unsupported_op / failed_extraction sentinel.
    """
```

`PlanResult` is a sum type:

```python
@dataclass(frozen=True)
class PlanOk:
    instance_tree: InstanceTree
    new_prototypes: list[PrototypeCandidate]

@dataclass(frozen=True)
class PlanUnsupported:
    missing_op: str

@dataclass(frozen=True)
class PlanFailed:
    reason: str

PlanResult = Union[PlanOk, PlanUnsupported, PlanFailed]
```

### 7.4 `reuse.py`

```python
CONTEXT_VARIANT_TRIGGER = 0.90  # cached from CLI --iou-gate

def decide_prototype(
    component_char: str,
    context_char: str,
    mmh: dict,
    existing: ProtoIndex,
    gate: float,
) -> tuple[Prototype, Prototype | None]:
    """Return (chosen_prototype, canonical_for_variant_edge_or_None)."""
```

The returned tuple's second element is used by `batch.py` to write
the `variant_of` edge.

### 7.5 `batch.py`

Orchestrator — called by `olik extract auto` CLI handler:

```python
def run_batch(
    count: int,
    seed: int,
    iou_gate: float,
    dry_run: bool,
) -> BatchReport:
    cjk_entries = load_cjk_decomp()
    all_chars   = load_moe_4808()
    mmh         = load_mmh_graphics()

    db = connect(); ensure_schema(db)
    filled = {row["char"] for row in db.query("SELECT char FROM glyph;")[0]["result"]}
    buckets = select_buckets(all_chars, filled, count, seed)

    report = BatchReport(seed=seed, iou_gate=iou_gate)
    run_id = create_extraction_run(db, seed, iou_gate) if not dry_run else None

    for ch in buckets:
        result = plan_char(ch, cjk_entries[ch], mmh, proto_index)
        match result:
            case PlanUnsupported(missing_op):
                report.unsupported += 1
                if not dry_run:
                    upsert_glyph_stub(db, ch, "unsupported_op", missing_op=missing_op, run=run_id)
            case PlanFailed(reason):
                report.failed += 1
                if not dry_run:
                    upsert_glyph_stub(db, ch, "failed_extraction", extraction_error=reason, run=run_id)
            case PlanOk(tree, new_protos):
                record = compose_and_emit(tree)
                status = "verified" if record.iou_mean >= iou_gate else "needs_review"
                report.add_status(status)
                if not dry_run:
                    sync_protos_and_variants(db, new_protos)  # writes variant_of edges
                    upsert_glyph(db, record, status=status, run=run_id)

    if not dry_run:
        finalize_extraction_run(db, run_id, report)
    return report
```

### 7.6 `status.py`

```python
class Status(str, Enum):
    VERIFIED         = "verified"
    NEEDS_REVIEW     = "needs_review"
    UNSUPPORTED_OP   = "unsupported_op"
    FAILED_EXTRACTION = "failed_extraction"

VALID_TRANSITIONS: dict[Status, set[Status]] = {
    Status.UNSUPPORTED_OP:   {Status.VERIFIED, Status.NEEDS_REVIEW, Status.FAILED_EXTRACTION},
    Status.FAILED_EXTRACTION:{Status.VERIFIED, Status.NEEDS_REVIEW, Status.UNSUPPORTED_OP},
    Status.NEEDS_REVIEW:     {Status.VERIFIED, Status.NEEDS_REVIEW},  # re-run can stay at review
    Status.VERIFIED:         {Status.VERIFIED, Status.NEEDS_REVIEW},  # re-run never worsens unless IoU drops
}
```

Transitions are enforced by `upsert_glyph` — if the new status isn't in
the prior status's allowed set, raise.

## 8. Testing strategy

### 8.1 Unit

- `test_ops.py` — `resolve_mode("a") == "left_right"`, unknown ops
  return `None`.
- `test_reuse.py` — synthetic prototypes; assert reuse when canonical
  passes IoU; assert variant created (with `variant_of` reason
  `"iou_fallback"`) when it doesn't.
- `test_status.py` — invalid transition raises; valid transitions
  pass.
- `test_charlist.py` — `select_buckets` is deterministic per seed;
  excludes already-filled.

### 8.2 Integration (against ephemeral SurrealDB fixture)

- `test_bulk_smoke.py` — run `run_batch(count=20, seed=0, iou_gate=0.90)`;
  assert status counts sum to 20; assert each glyph row has non-NONE
  status.
- `test_bulk_retry.py` — create a `unsupported_op` row manually, add a
  new mode to the LUT, run `olik extract retry --status unsupported_op`,
  assert the row's status flipped and its `missing_op` cleared.
- `test_bulk_reproducible.py` — run twice with same seed + count;
  assert the selected bucket list is identical.

### 8.3 End-to-end (manual / CI-optional)

- `task extract:batch-500` against the dev DB; expected approx
  distribution: verified 200-350, needs_review 100-200, unsupported_op
  50-150. Actual numbers calibrated on first real run.

## 9. Data-file bootstrap

1. Download `moe_4808.txt` from upstream Watermelonnn repo (source
   attribution in `LICENSE-moe-4808`).
2. Commit as-is under `project/py/data/moe_4808.txt`.
3. `.gitignore` already carves out `project/py/data/*` with `!` allow
   for specific data files — add `!project/py/data/moe_4808.txt` and
   `!project/py/data/LICENSE-moe-4808` alongside the existing
   cjk-decomp allow.

## 10. Migration / compatibility

- The 4 existing seed glyphs keep their hand-authored YAML entries; a
  one-time `olik extract backfill-status` sets their `status=verified`
  (they already meet the gate).
- The running `hanfont/olik` DB picks up the new schema fields the
  next time `ensure_schema()` runs (DEFINE FIELD overwrite is safe).
- `olik build` and `olik db sync` behavior unchanged for the 4 seeds.
- `olik db export` learns to round-trip the new fields (status,
  missing_op, extraction_error, extraction_run) — straightforward
  since the JSON already carries arbitrary key/value pairs.

## 11. Risks & open questions

- **Operator coverage drift.** We've mapped 4 ops today. The real 4808
  set almost certainly uses more. If `--count 500` returns > 30 %
  `unsupported_op`, it's a signal to expand the LUT inside Plan 09's
  scope. If it's 5–30 %, accept the gap and target in Plan 09.x.
- **MMH stroke order assumptions.** The planner assumes MMH's stroke
  order matches IDS component order (e.g. for `a` layout, the first
  N strokes belong to the left component). This breaks for the
  國-class non-contiguous case. For now, the IoU gate catches it and
  the char lands in `needs_review`.
- **Prototype-library explosion.** Reuse-first limits variant creation
  but some chars may still trigger many. We'll cap at 2 variants per
  canonical prototype by default; over the cap, the third char just
  goes into `needs_review` with an error note. Cap is configurable
  (`--max-variants-per-proto`).
- **Char selection stability.** If `moe_4808.txt` upstream changes
  order, the `--seed 42` bucket list changes too. The `LICENSE-moe-4808`
  file pins a specific commit hash of the upstream source, and
  `extraction_run` records it so retroactive reproducibility is
  achievable if someone wants to rerun an old batch.
- **DB pressure.** 500 glyph upserts + new prototypes + edges × a few
  per glyph is O(a few thousand) queries. Well within SurrealDB's
  throughput for local dev; no tuning needed.

## 12. Out of scope / follow-up plans

- **Plan 10** (admin UI) — surfaces `status = needs_review` as a review
  queue. First consumer of the Plan 09 status enum; first real UI
  over the bucket count.
- **Plan 11** (ComfyUI) — unchanged by Plan 09. `style_variant` stays
  empty until Plan 11 workflows populate it.
- **Plan 12** (coverage expansion) — bulk adds remaining operators
  (e.g. `wb` in its various parenthesized forms), re-targets
  `status=unsupported_op` buckets. Same pipeline, larger LUT.
- **Plan 13** (data re-ingest) — if MoE or cjk-decomp upstream bumps,
  a single `olik extract retry --all` re-runs the whole filled set
  against current upstream data; diffs get surfaced via IoU
  regressions.
