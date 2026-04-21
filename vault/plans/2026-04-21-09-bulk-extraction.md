---
title: "Plan 09 — Bulk extraction pipeline"
created: 2026-04-21
tags: [type/plan, topic/scene-graph, topic/extraction]
source: self
spec: "[[2026-04-21-bulk-extraction-design]]"
status: draft
phase: 9
depends-on:
  - "[[2026-04-21-03-python-compose-cli]]"
  - "[[2026-04-21-08-surrealdb-foundation]]"
---

# Plan 09 — Bulk extraction pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship `olik extract auto/retry/report/list/backfill-status` — an auto-planning bulk extraction pipeline that reads MoE 4808 + cjk-decomp + MMH, picks random empty buckets, runs the existing compose/emit pipeline with a reuse-first prototype policy, triages each result into a four-state status enum persisted on the `glyph` row, and upserts into SurrealDB. Populates the first 500 random buckets as the smoke test.

**Architecture:** New `olik_font.bulk.*` module tree (charlist, ops, planner, reuse, status, batch) on top of Plan 08's SurrealDB sink. Auto-planner synthesises an in-memory `ExtractionPlan` from cjk-decomp + MMH and feeds it to the existing compose/emit functions; no YAML file is written. A four-value `status` enum on each glyph row plus a new `variant_of` graph edge capture outcome + context-variant lineage. Reuse-first with IoU-triggered fallback caps runaway prototype growth.

**Tech Stack:** Python 3.11, SurrealDB 3.0.4, existing olik_font compose/emit machinery, pytest.

---

## File Structure

```
project/py/
├── data/
│   ├── moe_4808.txt                                   # NEW — committed char list
│   └── LICENSE-moe-4808                               # NEW — attribution
├── src/olik_font/
│   ├── bulk/                                          # NEW module tree
│   │   ├── __init__.py
│   │   ├── charlist.py                                # load_moe_4808 + select_buckets
│   │   ├── ops.py                                     # cjk-decomp op → compose mode
│   │   ├── status.py                                  # Status enum + transitions
│   │   ├── reuse.py                                   # ProtoIndex + decide_prototype
│   │   ├── planner.py                                 # plan_char → PlanResult sum type
│   │   └── batch.py                                   # run_batch orchestrator
│   ├── sink/
│   │   ├── schema.py                                  # + status field + variant_of edge
│   │   └── surrealdb.py                               # + upsert_glyph_stub + upsert_variant_of
│   └── cli.py                                         # + `extract` subcommand tree
└── tests/
    ├── test_bulk_charlist.py                          # deterministic bucket selection
    ├── test_bulk_ops.py                               # operator LUT
    ├── test_bulk_status.py                            # enum transitions
    ├── test_bulk_reuse.py                             # reuse vs variant decision
    ├── test_bulk_planner.py                           # plan_char outcomes
    ├── test_bulk_batch.py                             # orchestrator roundtrip
    └── test_cli_extract.py                            # CLI verbs end-to-end

Taskfile.yml                                           # + extract:batch-500 / fetch-moe-4808 lanes
.gitignore                                             # (already covers infra/)
```

Constraints:
- No changes to existing `emit/`, `compose/`, `decompose/` modules. Auto-planner builds `ExtractionPlan` objects using the existing `PrototypePlan` / `GlyphPlan` / `GlyphNodePlan` dataclasses from `olik_font.prototypes.extraction_plan`.
- The 4 seed YAML entries keep precedence: `run_batch` skips chars already present in `extraction_plan.yaml` AND already filled in the DB. Backfill for the seeds uses `olik extract backfill-status`.

---

## Task 1: Status enum + schema additions

**Files:**
- Create: `project/py/src/olik_font/bulk/__init__.py`
- Create: `project/py/src/olik_font/bulk/status.py`
- Create: `project/py/tests/test_bulk_status.py`
- Modify: `project/py/src/olik_font/sink/schema.py`
- Modify: `project/py/src/olik_font/sink/surrealdb.py`

- [ ] **Step 1: `bulk/__init__.py`** (empty module marker)

```python
"""Bulk auto-extraction pipeline (Plan 09)."""
```

- [ ] **Step 2: Write failing test for `bulk/status.py`**

```python
# project/py/tests/test_bulk_status.py
"""Status enum + transitions."""

from __future__ import annotations

import pytest

from olik_font.bulk.status import Status, assert_transition


def test_status_values() -> None:
    assert Status.VERIFIED.value          == "verified"
    assert Status.NEEDS_REVIEW.value      == "needs_review"
    assert Status.UNSUPPORTED_OP.value    == "unsupported_op"
    assert Status.FAILED_EXTRACTION.value == "failed_extraction"


def test_transition_unsupported_to_verified_ok() -> None:
    assert_transition(Status.UNSUPPORTED_OP, Status.VERIFIED)


def test_transition_verified_to_needs_review_ok() -> None:
    assert_transition(Status.VERIFIED, Status.NEEDS_REVIEW)


def test_transition_from_none_always_ok() -> None:
    """First-write transitions (prior=NONE) are always allowed."""
    for target in Status:
        assert_transition(None, target)


def test_transition_between_terminal_failures_ok() -> None:
    """A re-run can flip between the three failure states as the LUT grows."""
    assert_transition(Status.UNSUPPORTED_OP, Status.FAILED_EXTRACTION)
    assert_transition(Status.FAILED_EXTRACTION, Status.UNSUPPORTED_OP)
```

- [ ] **Step 3: Run — must fail**

```bash
cd project/py && .venv/bin/pytest tests/test_bulk_status.py -v
```

Expected: ImportError on `olik_font.bulk.status`.

- [ ] **Step 4: Implement `bulk/status.py`**

```python
# project/py/src/olik_font/bulk/status.py
"""Status enum for the bulk extraction pipeline (Plan 09)."""

from __future__ import annotations

from enum import Enum


class Status(str, Enum):
    VERIFIED          = "verified"
    NEEDS_REVIEW      = "needs_review"
    UNSUPPORTED_OP    = "unsupported_op"
    FAILED_EXTRACTION = "failed_extraction"


# Any transition is allowed between the four states. The enum exists so
# callers check spelling + `ASSERT $value IN [...]` on the DB side catches
# bad values early. Keeping this permissive avoids tripping re-run flows
# when the operator LUT expands and a former `unsupported_op` becomes
# `verified` (or, rarely, drops back to `failed_extraction` for MMH
# reasons).
def assert_transition(prior: Status | None, target: Status) -> None:
    """Raise if the transition is invalid. Currently all transitions
    (including from None) are permitted; function exists as a named
    guardrail point for future tightening.
    """
    if not isinstance(target, Status):
        raise TypeError(f"target must be Status, got {type(target).__name__}")
    # No further constraints in pass 1.
```

- [ ] **Step 5: Run — must pass**

```bash
.venv/bin/pytest tests/test_bulk_status.py -v
```

Expected: 5 passed.

- [ ] **Step 6: Extend `sink/schema.py` DDL**

Replace the `DDL` constant in `project/py/src/olik_font/sink/schema.py` with:

```python
DDL = """
-- glyph: one row per character, embedded stroke/layout data
DEFINE TABLE glyph SCHEMALESS;
DEFINE INDEX glyph_char_uniq ON glyph FIELDS char UNIQUE;
DEFINE INDEX glyph_stroke_ct ON glyph FIELDS stroke_count;
DEFINE INDEX glyph_radical   ON glyph FIELDS radical;
DEFINE INDEX glyph_iou_mean  ON glyph FIELDS iou_mean;
DEFINE INDEX glyph_status    ON glyph FIELDS status;

-- prototype
DEFINE TABLE prototype SCHEMALESS;
DEFINE INDEX proto_id_uniq ON prototype FIELDS id UNIQUE;
DEFINE INDEX proto_name    ON prototype FIELDS name;

-- rule
DEFINE TABLE rule SCHEMALESS;
DEFINE INDEX rule_id_uniq ON rule FIELDS id UNIQUE;
DEFINE INDEX rule_bucket  ON rule FIELDS bucket;

DEFINE TABLE rule_trace SCHEMALESS;
DEFINE INDEX rt_glyph_order ON rule_trace FIELDS glyph, order;

DEFINE TABLE extraction_run SCHEMALESS;

DEFINE TABLE style_variant SCHEMALESS;
DEFINE INDEX sv_char_style ON style_variant FIELDS char, style_name UNIQUE;

DEFINE TABLE comfyui_job SCHEMALESS;
DEFINE INDEX cj_id_uniq ON comfyui_job FIELDS id UNIQUE;

-- Edges
DEFINE TABLE uses       SCHEMALESS;
DEFINE TABLE cites      SCHEMALESS;
DEFINE TABLE variant_of SCHEMALESS;
DEFINE INDEX variant_of_in_out ON variant_of FIELDS in, out UNIQUE;
"""
```

- [ ] **Step 7: Add sink helpers for stubs + variant_of edges**

Append to `project/py/src/olik_font/sink/surrealdb.py`:

```python
def upsert_glyph_stub(
    db: Surreal,
    char: str,
    status: str,
    *,
    missing_op: str | None = None,
    extraction_error: str | None = None,
    extraction_run: str | None = None,
) -> None:
    """Insert-or-update a bucket row with no stroke data — used for
    `unsupported_op` and `failed_extraction` outcomes so every bucket
    in the batch produces a DB row.
    """
    body: dict[str, Any] = {"char": char, "status": status}
    if missing_op is not None:
        body["missing_op"] = missing_op
    if extraction_error is not None:
        body["extraction_error"] = extraction_error
    if extraction_run is not None:
        body["extraction_run"] = extraction_run
    db.query(
        "UPDATE type::thing('glyph', $char) MERGE $data;",
        {"char": char, "data": body},
    )


def upsert_variant_of_edge(
    db: Surreal,
    variant_id: str,
    canonical_id: str,
    reason: str = "iou_fallback",
) -> None:
    """Create `prototype:variant -> variant_of -> prototype:canonical`
    if absent. Idempotent via the variant_of_in_out UNIQUE index — a
    duplicate insert is an error, so we use BEGIN...IF NOT EXISTS
    semantics via SELECT-first.
    """
    existing = db.query(
        "SELECT id FROM variant_of "
        "WHERE in = type::thing('prototype', $v) "
        "  AND out = type::thing('prototype', $c) LIMIT 1;",
        {"v": variant_id, "c": canonical_id},
    )[0]["result"]
    if existing:
        return
    db.query(
        "RELATE type::thing('prototype', $v)->variant_of"
        "->type::thing('prototype', $c) CONTENT { reason: $r };",
        {"v": variant_id, "c": canonical_id, "r": reason},
    )
```

- [ ] **Step 8: Run existing sink tests to confirm no regression**

```bash
.venv/bin/pytest tests/test_sink_*.py -v
```

Expected: all prior sink tests still pass (no behavioral change to pre-existing helpers).

- [ ] **Step 9: Commit**

```bash
git add project/py/src/olik_font/bulk/__init__.py project/py/src/olik_font/bulk/status.py project/py/src/olik_font/sink/schema.py project/py/src/olik_font/sink/surrealdb.py project/py/tests/test_bulk_status.py
git commit -m "feat(bulk): Status enum + schema adds (variant_of, glyph.status index)"
```

---

## Task 2: MoE 4808 char list + `charlist.py`

**Files:**
- Create: `project/py/data/moe_4808.txt`
- Create: `project/py/data/LICENSE-moe-4808`
- Modify: `.gitignore` (allow the two new files through the `data/*` block)
- Create: `project/py/src/olik_font/bulk/charlist.py`
- Create: `project/py/tests/test_bulk_charlist.py`

- [ ] **Step 1: Download the char list**

```bash
curl -fsSL -o project/py/data/moe_4808.txt \
  "https://raw.githubusercontent.com/Watermelonnn/ChineseUsefulToolKit/master/%E6%95%99%E8%82%B2%E9%83%A8%E5%B8%B8%E7%94%A8%E5%AD%974808%E5%AD%97.txt"
wc -l project/py/data/moe_4808.txt
```

Expected: a file with ~4808 distinct CJK codepoints (may be one-per-line or whitespace-separated — the loader strips + deduplicates).

- [ ] **Step 2: Write `LICENSE-moe-4808`**

```
# MoE 4808 common-use character list

Source: https://github.com/Watermelonnn/ChineseUsefulToolKit
File:   教育部常用字4808字.txt (master branch)

This list enumerates Taiwan's Ministry of Education 常用國字標準字體表
(4808 characters). The upstream repository does not declare an explicit
license; the list itself is a public dataset published by the MoE.

Retrieved: 2026-04-21 (via scripts/data-regen.sh at implementation time)
```

- [ ] **Step 3: Update `.gitignore`**

Add `!project/py/data/moe_4808.txt` and `!project/py/data/LICENSE-moe-4808` next to the existing `cjk-decomp.json` allow lines:

```gitignore
# Committed dataset snapshot (Apache-2.0 from amake/cjk-decomp) and its
# license note — regenerate via `task data:regen-cjk-decomp`.
!project/py/data/cjk-decomp.json
!project/py/data/LICENSE-cjk-decomp
# MoE 4808 常用字 char list (public dataset from Watermelonnn/ChineseUsefulToolKit).
!project/py/data/moe_4808.txt
!project/py/data/LICENSE-moe-4808
```

- [ ] **Step 4: Write failing tests for `charlist.py`**

```python
# project/py/tests/test_bulk_charlist.py
"""MoE 4808 loader + deterministic bucket selection."""

from __future__ import annotations

from olik_font.bulk.charlist import load_moe_4808, select_buckets


def test_load_moe_4808_returns_unique_chars() -> None:
    chars = load_moe_4808()
    assert len(chars) >= 4000, f"expected ~4808 chars, got {len(chars)}"
    assert len(set(chars)) == len(chars), "duplicates present"
    # Sanity: all entries are single CJK codepoints.
    assert all(len(c) == 1 and "\u4e00" <= c <= "\u9fff" for c in chars[:100])


def test_select_buckets_deterministic_per_seed() -> None:
    pool = [chr(0x4E00 + i) for i in range(200)]  # 一 … for 200 codepoints
    a = select_buckets(pool, already_filled=set(), count=20, seed=42)
    b = select_buckets(pool, already_filled=set(), count=20, seed=42)
    c = select_buckets(pool, already_filled=set(), count=20, seed=43)
    assert a == b
    assert a != c
    assert len(a) == 20
    assert len(set(a)) == 20


def test_select_buckets_excludes_already_filled() -> None:
    pool = [chr(0x4E00 + i) for i in range(50)]
    filled = set(pool[:10])
    picked = select_buckets(pool, already_filled=filled, count=10, seed=1)
    assert len(picked) == 10
    assert all(ch not in filled for ch in picked)


def test_select_buckets_caps_at_available() -> None:
    pool = [chr(0x4E00 + i) for i in range(10)]
    filled = set(pool[:7])
    picked = select_buckets(pool, already_filled=filled, count=99, seed=0)
    # Only 3 available; result must be exactly those 3.
    assert len(picked) == 3
    assert set(picked) == set(pool[7:])
```

- [ ] **Step 5: Run — expect failure**

```bash
.venv/bin/pytest tests/test_bulk_charlist.py -v
```

Expected: ImportError on `olik_font.bulk.charlist`.

- [ ] **Step 6: Implement `charlist.py`**

```python
# project/py/src/olik_font/bulk/charlist.py
"""Load the MoE 4808 char list + deterministic bucket selection."""

from __future__ import annotations

import random
from pathlib import Path

_DATA_ROOT = Path(__file__).resolve().parents[3] / "data"
_MOE_FILE = _DATA_ROOT / "moe_4808.txt"


def _is_cjk(ch: str) -> bool:
    return len(ch) == 1 and (
        "\u4e00" <= ch <= "\u9fff" or  # CJK Unified
        "\u3400" <= ch <= "\u4dbf"     # CJK Extension A
    )


def load_moe_4808(path: Path | None = None) -> list[str]:
    """Return the list of CJK chars in the MoE 4808 file, deduplicated,
    preserving first-occurrence order.
    """
    src = path or _MOE_FILE
    raw = src.read_text(encoding="utf-8")
    seen: set[str] = set()
    out: list[str] = []
    for token in raw.replace("\n", " ").split():
        for ch in token:
            if _is_cjk(ch) and ch not in seen:
                seen.add(ch)
                out.append(ch)
    return out


def select_buckets(
    pool: list[str],
    already_filled: set[str],
    count: int,
    seed: int,
) -> list[str]:
    """Pick up to `count` chars from `pool` that aren't in
    `already_filled`. Deterministic per seed — sorts candidates by their
    index in `pool` first so the same (pool, filled) yields the same
    shuffle for the same seed.
    """
    candidates = [ch for ch in pool if ch not in already_filled]
    rng = random.Random(seed)
    rng.shuffle(candidates)
    return candidates[:count]
```

- [ ] **Step 7: Run — must pass**

```bash
.venv/bin/pytest tests/test_bulk_charlist.py -v
```

Expected: 4 passed.

- [ ] **Step 8: Commit**

```bash
git add project/py/data/moe_4808.txt project/py/data/LICENSE-moe-4808 .gitignore project/py/src/olik_font/bulk/charlist.py project/py/tests/test_bulk_charlist.py
git commit -m "feat(bulk): load_moe_4808 + deterministic bucket selection"
```

---

## Task 3: cjk-decomp operator → compose mode LUT

**Files:**
- Create: `project/py/src/olik_font/bulk/ops.py`
- Create: `project/py/tests/test_bulk_ops.py`

- [ ] **Step 1: Write failing tests**

```python
# project/py/tests/test_bulk_ops.py
"""cjk-decomp operator → compose mode mapping."""

from __future__ import annotations

from olik_font.bulk.ops import SUPPORTED_MODES, resolve_mode


def test_resolve_supported_ops() -> None:
    assert resolve_mode("a")     == "left_right"
    assert resolve_mode("d")     == "top_bottom"
    assert resolve_mode("s")     == "enclose"
    assert resolve_mode("r3tr")  == "repeat_triangle"


def test_resolve_unsupported_returns_none() -> None:
    assert resolve_mode("w")      is None
    assert resolve_mode("wb")     is None
    assert resolve_mode("nonsense") is None


def test_supported_modes_covers_olik_presets() -> None:
    # Sanity: the values of the LUT must all be real olik compose presets.
    from olik_font.prototypes.extraction_plan import Preset
    import typing
    valid = set(typing.get_args(Preset))
    assert SUPPORTED_MODES.issubset(valid)
```

- [ ] **Step 2: Run — expect failure**

```bash
.venv/bin/pytest tests/test_bulk_ops.py -v
```

Expected: ImportError.

- [ ] **Step 3: Implement `ops.py`**

```python
# project/py/src/olik_font/bulk/ops.py
"""cjk-decomp operator → olik compose mode LUT."""

from __future__ import annotations

# Mapping of cjk-decomp operator codes to olik compose Preset names.
# Unmapped operators → None (treated as unsupported_op by the planner).
OP_TO_MODE: dict[str, str] = {
    "a":    "left_right",      # 左右並列
    "d":    "top_bottom",      # 上下並列
    "s":    "enclose",         # 全包圍
    "r3tr": "repeat_triangle", # 品字形三疊
}

SUPPORTED_MODES: frozenset[str] = frozenset(OP_TO_MODE.values())


def resolve_mode(op: str) -> str | None:
    return OP_TO_MODE.get(op)
```

- [ ] **Step 4: Run — must pass**

```bash
.venv/bin/pytest tests/test_bulk_ops.py -v
```

Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add project/py/src/olik_font/bulk/ops.py project/py/tests/test_bulk_ops.py
git commit -m "feat(bulk): cjk-decomp op → compose mode LUT (4 initial ops)"
```

---

## Task 4: `ProtoIndex` + `decide_prototype`

**Files:**
- Create: `project/py/src/olik_font/bulk/reuse.py`
- Create: `project/py/tests/test_bulk_reuse.py`

- [ ] **Step 1: Write failing tests**

```python
# project/py/tests/test_bulk_reuse.py
"""Prototype reuse decision + context-variant fallback."""

from __future__ import annotations

from olik_font.bulk.reuse import ProtoIndex, ReuseDecision, decide_prototype
from olik_font.prototypes.extraction_plan import PrototypePlan


def _proto(id_: str, name: str, from_char: str, strokes: tuple[int, ...]) -> PrototypePlan:
    return PrototypePlan(
        id=id_, name=name, from_char=from_char,
        stroke_indices=strokes, roles=("meaning",), anchors={},
    )


def test_reuse_when_canonical_exists() -> None:
    idx = ProtoIndex(prototypes=[_proto("proto:tree", "木", "森", (0, 1, 2, 3))])
    decision = decide_prototype(
        component_char="木",
        context_char="林",
        index=idx,
        probe_iou=lambda _: 1.0,   # canonical fits perfectly
        gate=0.90,
        cap=2,
    )
    assert decision.chosen_id         == "proto:tree"
    assert decision.canonical_for_edge is None  # reuse — no variant edge
    assert decision.is_new_variant    is False


def test_variant_created_when_canonical_below_gate() -> None:
    idx = ProtoIndex(prototypes=[_proto("proto:tree", "木", "森", (0, 1, 2, 3))])
    decision = decide_prototype(
        component_char="木",
        context_char="林",
        index=idx,
        probe_iou=lambda _: 0.7,   # canonical doesn't fit → fall back
        gate=0.90,
        cap=2,
    )
    assert decision.chosen_id       == "proto:tree_in_林"
    assert decision.canonical_for_edge == "proto:tree"
    assert decision.is_new_variant  is True


def test_variant_reuse_when_context_match_exists() -> None:
    idx = ProtoIndex(prototypes=[
        _proto("proto:tree",     "木", "森", (0, 1, 2, 3)),
        _proto("proto:tree_in_林", "木", "林", (0, 1, 2, 3)),
    ])
    decision = decide_prototype(
        component_char="木", context_char="林",
        index=idx, probe_iou=lambda _: 0.7,
        gate=0.90, cap=2,
    )
    # Variant already exists for this context — reuse it, no new edge.
    assert decision.chosen_id       == "proto:tree_in_林"
    assert decision.canonical_for_edge is None
    assert decision.is_new_variant  is False


def test_new_prototype_when_none_exists() -> None:
    idx = ProtoIndex(prototypes=[])
    decision = decide_prototype(
        component_char="木", context_char="林",
        index=idx, probe_iou=lambda _: 1.0,
        gate=0.90, cap=2,
    )
    assert decision.chosen_id         == "proto:tree"  # derived from component_char
    assert decision.is_new_canonical  is True


def test_variant_cap_exceeded_signals_review() -> None:
    idx = ProtoIndex(prototypes=[
        _proto("proto:tree",        "木", "森", (0, 1, 2, 3)),
        _proto("proto:tree_in_桂",   "木", "桂", (0, 1, 2, 3)),
        _proto("proto:tree_in_松",   "木", "松", (0, 1, 2, 3)),
    ])
    decision = decide_prototype(
        component_char="木", context_char="橋",
        index=idx, probe_iou=lambda _: 0.5,  # canonical fails
        gate=0.90, cap=2,
    )
    # Cap is 2, two variants already exist → refuse to create a third.
    assert decision.chosen_id is None
    assert decision.cap_exceeded is True
```

- [ ] **Step 2: Run — must fail**

```bash
.venv/bin/pytest tests/test_bulk_reuse.py -v
```

Expected: ImportError on `olik_font.bulk.reuse`.

- [ ] **Step 3: Implement `reuse.py`**

```python
# project/py/src/olik_font/bulk/reuse.py
"""Prototype reuse policy with IoU-triggered context-variant fallback.

Canonical IDs: `proto:<component_name>` (e.g. `proto:tree` for 木).
Context variant IDs: `proto:<component_name>_in_<context_char>`
(e.g. `proto:tree_in_林`). The exact name stringification is the
responsibility of `name_to_slug`; callers never construct IDs themselves.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Iterable

from olik_font.prototypes.extraction_plan import PrototypePlan


# --- ID helpers -------------------------------------------------------------

# Hand-authored map for components whose "name" needs a specific ASCII
# slug so generated IDs stay stable and queryable. Fallback is `ord(ch)`.
_SLUGS: dict[str, str] = {
    "木": "tree",
    "日": "sun",
    "月": "moon",
    "氵": "water_3dots",
    "囗": "enclosure_box",
    "或": "huo",
    "龶": "sheng",
    "青": "qing",
}


def name_to_slug(name: str) -> str:
    """Deterministic ASCII slug for a component name."""
    return _SLUGS.get(name, f"u{ord(name[0]):04x}")


def canonical_id(component_name: str) -> str:
    return f"proto:{name_to_slug(component_name)}"


def variant_id(component_name: str, context_char: str) -> str:
    return f"proto:{name_to_slug(component_name)}_in_{context_char}"


# --- Data classes -----------------------------------------------------------

@dataclass(frozen=True)
class ProtoIndex:
    prototypes: list[PrototypePlan]

    @property
    def by_id(self) -> dict[str, PrototypePlan]:
        return {p.id: p for p in self.prototypes}

    def find_by_name(self, name: str) -> list[PrototypePlan]:
        return [p for p in self.prototypes if p.name == name]

    def canonical_for(self, component_name: str) -> PrototypePlan | None:
        cid = canonical_id(component_name)
        for p in self.prototypes:
            if p.id == cid:
                return p
        return None

    def variants_of(self, component_name: str) -> list[PrototypePlan]:
        """All `proto:X_in_Y` entries for a given component name `X`."""
        prefix = canonical_id(component_name) + "_in_"
        return [p for p in self.prototypes if p.id.startswith(prefix)]


@dataclass(frozen=True)
class ReuseDecision:
    chosen_id: str | None                 # None when cap_exceeded
    canonical_for_edge: str | None        # set → caller writes variant_of edge
    is_new_variant: bool = False          # caller extracts + upserts a new proto
    is_new_canonical: bool = False        # caller extracts + upserts a new proto
    cap_exceeded: bool = False            # caller marks glyph needs_review


# --- Decision logic ---------------------------------------------------------

def decide_prototype(
    component_char: str,
    context_char: str,
    index: ProtoIndex,
    probe_iou: Callable[[PrototypePlan], float],
    gate: float,
    cap: int,
) -> ReuseDecision:
    """Decide which prototype a component should resolve to.

    Order:
      1. If a variant already exists for this exact context, reuse it.
      2. Else if a canonical exists, probe its IoU against this context —
         reuse if >= gate.
      3. Else if canonical exists but IoU < gate, create a new variant
         (unless the cap is already reached).
      4. Else (no canonical exists), create a new canonical.
    """
    # 1. context-specific variant already known
    exact_variant = variant_id(component_char, context_char)
    for p in index.prototypes:
        if p.id == exact_variant:
            return ReuseDecision(chosen_id=exact_variant, canonical_for_edge=None)

    canonical = index.canonical_for(component_char)

    # 4. no canonical yet → extract one from the component itself
    if canonical is None:
        return ReuseDecision(
            chosen_id=canonical_id(component_char),
            canonical_for_edge=None,
            is_new_canonical=True,
        )

    # 2. canonical exists → try reuse
    if probe_iou(canonical) >= gate:
        return ReuseDecision(chosen_id=canonical.id, canonical_for_edge=None)

    # 3. fall back to a new variant (capped)
    existing_variants = index.variants_of(component_char)
    if len(existing_variants) >= cap:
        return ReuseDecision(
            chosen_id=None,
            canonical_for_edge=None,
            cap_exceeded=True,
        )
    return ReuseDecision(
        chosen_id=exact_variant,
        canonical_for_edge=canonical.id,
        is_new_variant=True,
    )
```

- [ ] **Step 4: Run — must pass**

```bash
.venv/bin/pytest tests/test_bulk_reuse.py -v
```

Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add project/py/src/olik_font/bulk/reuse.py project/py/tests/test_bulk_reuse.py
git commit -m "feat(bulk): decide_prototype with reuse-first + variant fallback + cap"
```

---

## Task 5: Auto-planner `plan_char`

**Files:**
- Create: `project/py/src/olik_font/bulk/planner.py`
- Create: `project/py/tests/test_bulk_planner.py`

- [ ] **Step 1: Write failing tests**

```python
# project/py/tests/test_bulk_planner.py
"""plan_char — auto-build ExtractionPlan fragments from cjk-decomp."""

from __future__ import annotations

from olik_font.bulk.planner import (
    PlanFailed, PlanOk, PlanUnsupported, plan_char,
)
from olik_font.bulk.reuse import ProtoIndex


MINIMAL_MMH = {
    "明": {"character": "明", "strokes": ["M0", "M1", "M2", "M3", "M4", "M5", "M6", "M7"], "medians": [[]]*8},
    "日": {"character": "日", "strokes": ["M0"]*4, "medians": [[]]*4},
    "月": {"character": "月", "strokes": ["M0"]*4, "medians": [[]]*4},
}


def test_plan_char_supported_op_returns_ok() -> None:
    result = plan_char(
        char="明",
        cjk_entry={"operator": "a", "components": ["日", "月"]},
        mmh=MINIMAL_MMH,
        index=ProtoIndex(prototypes=[]),
        probe_iou=lambda _: 1.0,
        gate=0.90,
        cap=2,
    )
    assert isinstance(result, PlanOk)
    assert result.glyph_plan.preset == "left_right"
    assert len(result.glyph_plan.children) == 2
    # Two new canonical prototypes (proto:sun, proto:moon) were selected.
    assert {p.id for p in result.new_prototypes} == {"proto:sun", "proto:moon"}


def test_plan_char_unsupported_op_returns_sentinel() -> None:
    result = plan_char(
        char="彌",
        cjk_entry={"operator": "wb", "components": ["弓", "爾"]},
        mmh=MINIMAL_MMH,
        index=ProtoIndex(prototypes=[]),
        probe_iou=lambda _: 1.0,
        gate=0.90, cap=2,
    )
    assert isinstance(result, PlanUnsupported)
    assert result.missing_op == "wb"


def test_plan_char_missing_mmh_returns_failed() -> None:
    result = plan_char(
        char="齉",
        cjk_entry={"operator": "a", "components": ["鼻", "囊"]},
        mmh=MINIMAL_MMH,
        index=ProtoIndex(prototypes=[]),
        probe_iou=lambda _: 1.0,
        gate=0.90, cap=2,
    )
    assert isinstance(result, PlanFailed)
    assert "MMH" in result.reason


def test_plan_char_variant_cap_exceeded_returns_failed() -> None:
    from olik_font.prototypes.extraction_plan import PrototypePlan
    # Canonical + 2 existing variants for 月 → cap (default 2) exhausted.
    existing = [
        PrototypePlan(id="proto:moon",      name="月", from_char="明",
                      stroke_indices=(0,1,2,3), roles=("meaning",), anchors={}),
        PrototypePlan(id="proto:moon_in_朋", name="月", from_char="朋",
                      stroke_indices=(0,1,2,3), roles=("meaning",), anchors={}),
        PrototypePlan(id="proto:moon_in_期", name="月", from_char="期",
                      stroke_indices=(0,1,2,3), roles=("meaning",), anchors={}),
    ]
    result = plan_char(
        char="朔",
        cjk_entry={"operator": "a", "components": ["屰", "月"]},
        mmh={**MINIMAL_MMH, "朔": MINIMAL_MMH["明"], "屰": MINIMAL_MMH["日"]},
        index=ProtoIndex(prototypes=existing),
        probe_iou=lambda _: 0.5,  # force fallback → cap hit
        gate=0.90, cap=2,
    )
    assert isinstance(result, PlanFailed)
    assert "cap" in result.reason.lower()
```

- [ ] **Step 2: Run — must fail**

```bash
.venv/bin/pytest tests/test_bulk_planner.py -v
```

Expected: ImportError.

- [ ] **Step 3: Implement `planner.py`**

```python
# project/py/src/olik_font/bulk/planner.py
"""Auto-plan a single character from its cjk-decomp entry + MMH data."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Union

from olik_font.bulk.ops import resolve_mode
from olik_font.bulk.reuse import (
    ProtoIndex, ReuseDecision, canonical_id, decide_prototype, variant_id,
)
from olik_font.prototypes.extraction_plan import (
    GlyphNodePlan, GlyphPlan, PrototypePlan,
)


@dataclass(frozen=True)
class PlanOk:
    glyph_plan: GlyphPlan
    new_prototypes: list[PrototypePlan]                      # unpersisted
    variant_edges: list[tuple[str, str]] = field(default_factory=list)  # (variant_id, canonical_id)


@dataclass(frozen=True)
class PlanUnsupported:
    missing_op: str


@dataclass(frozen=True)
class PlanFailed:
    reason: str


PlanResult = Union[PlanOk, PlanUnsupported, PlanFailed]


def _stroke_range_for_component(
    context_char: str, component_index: int, total_components: int, mmh_strokes: int,
) -> tuple[int, ...]:
    """Assign MMH stroke indices to a component in an N-component layout.

    Naive split: equal-sized contiguous chunks. Known to be wrong for the
    國-class non-contiguous case; the IoU gate catches those and the glyph
    lands in needs_review (see spec §11).
    """
    size = mmh_strokes // total_components
    start = component_index * size
    # Last component absorbs any remainder.
    end = mmh_strokes if component_index == total_components - 1 else start + size
    return tuple(range(start, end))


def _extract_new_prototype(
    component_name: str,
    proto_id: str,
    context_char: str,
    index_in_context: int,
    total_components: int,
    mmh: dict,
) -> PrototypePlan:
    """Synthesise a PrototypePlan pointed at `context_char`'s strokes for
    this component. Used by both first-time canonical creation and
    context-variant fallback.
    """
    mmh_entry = mmh.get(context_char)
    if mmh_entry is None:
        raise RuntimeError(f"missing MMH entry for {context_char}")
    n = len(mmh_entry["strokes"])
    strokes = _stroke_range_for_component(context_char, index_in_context, total_components, n)
    return PrototypePlan(
        id=proto_id,
        name=component_name,
        from_char=context_char,
        stroke_indices=strokes,
        roles=("meaning",),
        anchors={},
    )


def plan_char(
    char: str,
    cjk_entry: dict,
    mmh: dict,
    index: ProtoIndex,
    probe_iou: Callable[[PrototypePlan], float],
    gate: float,
    cap: int,
) -> PlanResult:
    """Return a PlanResult for `char`.

    * PlanUnsupported — operator not in the LUT.
    * PlanFailed      — MMH entry missing, or variant cap exhausted.
    * PlanOk          — a synthesised GlyphPlan + any new prototypes to
                        upsert. Does not touch the DB.
    """
    op = cjk_entry.get("operator", "")
    mode = resolve_mode(op)
    if mode is None:
        return PlanUnsupported(missing_op=op or "<empty>")

    if char not in mmh:
        return PlanFailed(reason=f"MMH missing {char}")

    components: list[str] = list(cjk_entry.get("components", []))
    if len(components) == 0:
        return PlanFailed(reason="cjk-decomp has no components")

    new_protos: list[PrototypePlan] = []
    variant_edges: list[tuple[str, str]] = []
    child_nodes: list[GlyphNodePlan] = []

    for i, comp_name in enumerate(components):
        decision = decide_prototype(
            component_char=comp_name, context_char=char,
            index=index, probe_iou=probe_iou, gate=gate, cap=cap,
        )
        if decision.cap_exceeded:
            return PlanFailed(reason=f"variant cap exceeded for {comp_name}")

        if decision.is_new_canonical:
            proto = _extract_new_prototype(
                comp_name, decision.chosen_id, char, i, len(components), mmh,
            )
            new_protos.append(proto)
        elif decision.is_new_variant:
            proto = _extract_new_prototype(
                comp_name, decision.chosen_id, char, i, len(components), mmh,
            )
            new_protos.append(proto)
            assert decision.canonical_for_edge is not None
            variant_edges.append((decision.chosen_id, decision.canonical_for_edge))

        child_nodes.append(GlyphNodePlan(prototype_ref=decision.chosen_id, mode="keep"))

    # Handle repeat_triangle separately — single prototype_ref + count.
    if mode == "repeat_triangle":
        proto_ref = child_nodes[0].prototype_ref
        glyph_plan = GlyphPlan(preset=mode, prototype_ref=proto_ref, count=len(components))
    else:
        glyph_plan = GlyphPlan(preset=mode, children=tuple(child_nodes))

    return PlanOk(
        glyph_plan=glyph_plan,
        new_prototypes=new_protos,
        variant_edges=variant_edges,
    )
```

- [ ] **Step 4: Run — must pass**

```bash
.venv/bin/pytest tests/test_bulk_planner.py -v
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add project/py/src/olik_font/bulk/planner.py project/py/tests/test_bulk_planner.py
git commit -m "feat(bulk): plan_char auto-plans from cjk-decomp + MMH"
```

---

## Task 6: Batch orchestrator `run_batch`

**Files:**
- Create: `project/py/src/olik_font/bulk/batch.py`
- Create: `project/py/tests/test_bulk_batch.py`

- [ ] **Step 1: Write failing test**

```python
# project/py/tests/test_bulk_batch.py
"""run_batch — orchestrates bucket selection + planning + upsert."""

from __future__ import annotations

import pytest

from olik_font.bulk.batch import BatchReport, run_batch
from olik_font.bulk.status import Status
from olik_font.sink.connection import DbConfig, connect
from olik_font.sink.schema import ensure_schema


def test_run_batch_status_counts_sum_to_count(
    surreal_ephemeral: DbConfig,
) -> None:
    """Smoke: count=10 run produces 10 rows with non-NONE status."""
    db = connect(surreal_ephemeral)
    ensure_schema(db)

    report: BatchReport = run_batch(
        db=db,
        count=10,
        seed=0,
        iou_gate=0.90,
        cap=2,
    )
    total = (
        report.counts[Status.VERIFIED]
        + report.counts[Status.NEEDS_REVIEW]
        + report.counts[Status.UNSUPPORTED_OP]
        + report.counts[Status.FAILED_EXTRACTION]
    )
    assert total == report.selected
    assert total <= 10  # available buckets may be less than requested

    rows = db.query("SELECT char, status FROM glyph;")[0]["result"]
    assert len(rows) == total
    assert all(r["status"] in {s.value for s in Status} for r in rows)


def test_run_batch_skips_already_filled(
    surreal_ephemeral: DbConfig,
) -> None:
    db = connect(surreal_ephemeral)
    ensure_schema(db)
    # Pre-seed one char as "verified".
    db.query(
        "UPDATE type::thing('glyph', '明') MERGE "
        "{ char: '明', status: 'verified', iou_mean: 1.0 };"
    )
    report = run_batch(db=db, count=5, seed=0, iou_gate=0.90, cap=2)
    # 明 must not reappear in the batch.
    assert "明" not in report.selected_chars


def test_run_batch_reproducible_per_seed(
    surreal_ephemeral: DbConfig,
) -> None:
    db = connect(surreal_ephemeral)
    ensure_schema(db)
    r1 = run_batch(db=db, count=5, seed=42, iou_gate=0.90, cap=2, dry_run=True)
    r2 = run_batch(db=db, count=5, seed=42, iou_gate=0.90, cap=2, dry_run=True)
    assert r1.selected_chars == r2.selected_chars
```

- [ ] **Step 2: Run — must fail**

```bash
.venv/bin/pytest tests/test_bulk_batch.py -v
```

Expected: ImportError.

- [ ] **Step 3: Implement `batch.py`**

```python
# project/py/src/olik_font/bulk/batch.py
"""Orchestrator: select buckets → plan → compose → gate → upsert."""

from __future__ import annotations

import json
import platform
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from olik_font.bulk.charlist import load_moe_4808, select_buckets
from olik_font.bulk.planner import (
    PlanFailed, PlanOk, PlanUnsupported, plan_char,
)
from olik_font.bulk.reuse import ProtoIndex
from olik_font.bulk.status import Status
from olik_font.compose.walk import compose_transforms
from olik_font.decompose.instance import build_instance_tree
from olik_font.emit.library import library_to_dict
from olik_font.emit.record import build_glyph_record
from olik_font.prototypes.extract import extract_all_prototypes
from olik_font.prototypes.extraction_plan import (
    ExtractionPlan, GlyphPlan, PrototypePlan,
)
from olik_font.rules.engine import apply_first_match, load_rules
from olik_font.sink.surrealdb import (
    upsert_glyph, upsert_glyph_stub, upsert_prototype,
    upsert_rule_trace, upsert_rules, upsert_variant_of_edge,
)
from olik_font.sources.makemeahanzi import fetch_mmh, load_mmh_graphics


_PY_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_MMH_DIR = _PY_ROOT / "data" / "mmh"
_DEFAULT_CJK    = _PY_ROOT / "data" / "cjk-decomp.json"
_DEFAULT_RULES  = _PY_ROOT / "src" / "olik_font" / "rules" / "rules.yaml"


@dataclass
class BatchReport:
    seed: int
    iou_gate: float
    selected: int = 0
    selected_chars: list[str] = field(default_factory=list)
    counts: Counter = field(default_factory=Counter)

    def add(self, status: Status) -> None:
        self.counts[status] += 1


def _load_cjk_entries(path: Path = _DEFAULT_CJK) -> dict[str, dict]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return raw.get("entries", {})


def _proto_index_from_db(db) -> ProtoIndex:
    rows = db.query("SELECT * FROM prototype;")[0]["result"]
    plans: list[PrototypePlan] = []
    for r in rows:
        plans.append(PrototypePlan(
            id=r["id"], name=r.get("name", ""),
            from_char=r.get("source", "")[-1:] if r.get("source") else "",
            stroke_indices=tuple(r.get("stroke_indices", ())),
            roles=tuple(r.get("roles", ("meaning",))),
            anchors=r.get("anchors", {}),
        ))
    return ProtoIndex(prototypes=plans)


def _create_extraction_run(db, seed: int, iou_gate: float) -> str:
    result = db.query(
        "CREATE extraction_run CONTENT $data RETURN id;",
        {"data": {
            "seed": seed, "iou_gate": iou_gate,
            "host": platform.node(),
        }},
    )[0]["result"][0]
    return str(result["id"])


def _finalize_extraction_run(db, run_id: str, report: BatchReport) -> None:
    db.query(
        "UPDATE $id MERGE { finished_at: time::now(), "
        "                    counts: $counts, "
        "                    chars_processed: $chars };",
        {
            "id": run_id,
            "counts": {s.value: report.counts[s] for s in Status},
            "chars": report.selected_chars,
        },
    )


def _trivial_probe_iou(_p: PrototypePlan) -> float:
    """Placeholder probe — assume canonical fits for the quick path.

    The real IoU of the composed result is measured after compose/emit;
    this function only gates the *reuse decision* speculatively. A low
    final IoU still lands the glyph in `needs_review`. Tightening this
    (speculative compose-probe) is a Plan-09.x polish.
    """
    return 1.0


def run_batch(
    db,
    count: int,
    seed: int,
    iou_gate: float,
    cap: int = 2,
    dry_run: bool = False,
    *,
    mmh_dir: Path = _DEFAULT_MMH_DIR,
    cjk_path: Path = _DEFAULT_CJK,
    rules_path: Path = _DEFAULT_RULES,
) -> BatchReport:
    # ---- data -------------------------------------------------------------
    mmh = load_mmh_graphics(fetch_mmh(mmh_dir))
    cjk = _load_cjk_entries(cjk_path)
    rules_meta = yaml.safe_load(rules_path.read_text(encoding="utf-8"))
    rules = load_rules(rules_path)

    # ---- buckets ----------------------------------------------------------
    pool = load_moe_4808()
    filled = {r["char"] for r in db.query("SELECT char FROM glyph;")[0]["result"]}
    buckets = select_buckets(pool, already_filled=filled, count=count, seed=seed)

    report = BatchReport(seed=seed, iou_gate=iou_gate,
                        selected=len(buckets), selected_chars=list(buckets))
    run_id: str | None = None
    if not dry_run and buckets:
        run_id = _create_extraction_run(db, seed, iou_gate)

    index = _proto_index_from_db(db)

    for ch in buckets:
        entry = cjk.get(ch)
        if entry is None:
            if not dry_run:
                upsert_glyph_stub(db, ch, Status.FAILED_EXTRACTION.value,
                                  extraction_error="cjk-decomp entry missing",
                                  extraction_run=run_id)
            report.add(Status.FAILED_EXTRACTION)
            continue

        result = plan_char(
            char=ch, cjk_entry=entry, mmh=mmh, index=index,
            probe_iou=_trivial_probe_iou, gate=iou_gate, cap=cap,
        )

        if isinstance(result, PlanUnsupported):
            if not dry_run:
                upsert_glyph_stub(db, ch, Status.UNSUPPORTED_OP.value,
                                  missing_op=result.missing_op,
                                  extraction_run=run_id)
            report.add(Status.UNSUPPORTED_OP)
            continue
        if isinstance(result, PlanFailed):
            if not dry_run:
                upsert_glyph_stub(db, ch, Status.FAILED_EXTRACTION.value,
                                  extraction_error=result.reason,
                                  extraction_run=run_id)
            report.add(Status.FAILED_EXTRACTION)
            continue

        # PlanOk — synthesise an ExtractionPlan with just this one char
        # and compose/emit via the existing pipeline.
        synthetic = ExtractionPlan(
            schema_version="0.1",
            prototypes=tuple(index.prototypes) + tuple(result.new_prototypes),
            glyphs={ch: result.glyph_plan},
        )
        try:
            library = extract_all_prototypes(synthetic, mmh)
            tree = build_instance_tree(ch, synthetic, library, mmh)
            composed = compose_transforms(tree, library)
            trace = apply_first_match(ch, tree, rules)
            record = build_glyph_record(ch, composed, library, trace, rules_meta)
        except Exception as exc:  # noqa: BLE001
            if not dry_run:
                upsert_glyph_stub(db, ch, Status.FAILED_EXTRACTION.value,
                                  extraction_error=f"{type(exc).__name__}: {exc}",
                                  extraction_run=run_id)
            report.add(Status.FAILED_EXTRACTION)
            continue

        iou = float(record.get("iou_report", {}).get("mean") or 0.0)
        status = Status.VERIFIED if iou >= iou_gate else Status.NEEDS_REVIEW
        report.add(status)

        if not dry_run:
            record["status"] = status.value
            record["iou_mean"] = iou
            record["extraction_run"] = run_id
            # upsert prototypes we just minted
            for proto in result.new_prototypes:
                upsert_prototype(db, {
                    "id": proto.id, "name": proto.name,
                    "source": f"extracted from {proto.from_char}",
                    "strokes": list(proto.stroke_indices),
                    "roles": list(proto.roles),
                    "anchors": proto.anchors,
                })
            for variant, canonical in result.variant_edges:
                upsert_variant_of_edge(db, variant, canonical)
            upsert_glyph(db, record)
            # Also keep the in-memory index up to date for the rest of the batch
            index = ProtoIndex(prototypes=list(index.prototypes) + list(result.new_prototypes))

    if not dry_run and run_id is not None:
        _finalize_extraction_run(db, run_id, report)

    # rules + rule_trace writes are skipped in Plan 09 to keep the loop
    # fast; Plan 10's admin UI doesn't need them to surface the status
    # queue. (Plan 11 or a Plan-09.x can fold them in.)
    _ = rules  # silence unused

    return report
```

- [ ] **Step 4: Run — must pass**

```bash
.venv/bin/pytest tests/test_bulk_batch.py -v
```

Expected: 3 passed. (Some chars may fall into `failed_extraction` because the ephemeral MMH data inside the test fixture is real → actual stroke counts; that's fine, we just assert statuses sum to the count.)

- [ ] **Step 5: Commit**

```bash
git add project/py/src/olik_font/bulk/batch.py project/py/tests/test_bulk_batch.py
git commit -m "feat(bulk): run_batch orchestrator with status triage"
```

---

## Task 7: CLI `olik extract auto` + `extract report` + `extract backfill-status`

**Files:**
- Modify: `project/py/src/olik_font/cli.py`
- Create: `project/py/tests/test_cli_extract.py`

- [ ] **Step 1: Write failing test**

```python
# project/py/tests/test_cli_extract.py
"""CLI: `olik extract auto|report|backfill-status|list|retry`."""

from __future__ import annotations

import pytest

from olik_font.cli import main
from olik_font.sink.connection import DbConfig, connect


def _set_env(monkeypatch: pytest.MonkeyPatch, cfg: DbConfig) -> None:
    for var, val in [
        ("OLIK_DB_URL",  cfg.url),
        ("OLIK_DB_NS",   cfg.namespace),
        ("OLIK_DB_NAME", cfg.database),
        ("OLIK_DB_USER", cfg.user),
        ("OLIK_DB_PASS", cfg.password),
    ]:
        monkeypatch.setenv(var, val)


def test_extract_auto_populates_buckets(
    surreal_ephemeral: DbConfig, monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_env(monkeypatch, surreal_ephemeral)
    monkeypatch.setattr("sys.argv", ["olik", "extract", "auto", "--count", "5", "--seed", "0"])
    rc = main()
    assert rc == 0
    db = connect(surreal_ephemeral)
    rows = db.query("SELECT char, status FROM glyph;")[0]["result"]
    assert 0 < len(rows) <= 5
    assert all(r.get("status") for r in rows)


def test_extract_report_prints_counts(
    surreal_ephemeral: DbConfig, monkeypatch: pytest.MonkeyPatch, capsys,
) -> None:
    _set_env(monkeypatch, surreal_ephemeral)
    monkeypatch.setattr("sys.argv", ["olik", "extract", "auto", "--count", "3", "--seed", "7"])
    main()
    monkeypatch.setattr("sys.argv", ["olik", "extract", "report"])
    rc = main()
    assert rc == 0
    out = capsys.readouterr().out
    assert "verified" in out
    assert "needs_review" in out


def test_extract_backfill_marks_seed_glyph_verified(
    surreal_ephemeral: DbConfig, monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_env(monkeypatch, surreal_ephemeral)
    db = connect(surreal_ephemeral)
    # Seed a glyph the old way (no status field)
    db.query("UPDATE type::thing('glyph', '明') MERGE "
             "{ char: '明', iou_mean: 1.0 };")
    monkeypatch.setattr("sys.argv", ["olik", "extract", "backfill-status", "--iou-gate", "0.90"])
    rc = main()
    assert rc == 0
    row = db.query("SELECT status FROM glyph WHERE char = '明';")[0]["result"][0]
    assert row["status"] == "verified"
```

- [ ] **Step 2: Confirm it fails**

```bash
.venv/bin/pytest tests/test_cli_extract.py -v
```

Expected: `SystemExit(2)` from argparse (unknown subcommand `extract`).

- [ ] **Step 3: Wire `extract` subtree into cli.py**

In `project/py/src/olik_font/cli.py`, add to the subparser block inside `_parse_args`:

```python
    # ---- extract (Plan 09 bulk pipeline) ----
    ext = subparsers.add_parser("extract", help="bulk auto-extraction pipeline")
    ext_sub = ext.add_subparsers(dest="ext_cmd", required=True)

    ext_auto = ext_sub.add_parser("auto", help="pick random empty buckets and extract them")
    ext_auto.add_argument("--count", type=int, required=True)
    ext_auto.add_argument("--seed", type=int, default=42)
    ext_auto.add_argument("--iou-gate", type=float, default=0.90)
    ext_auto.add_argument("--max-variants-per-proto", type=int, default=2)
    ext_auto.add_argument("--dry-run", action="store_true")

    ext_report = ext_sub.add_parser("report", help="print status breakdown")

    ext_back = ext_sub.add_parser("backfill-status",
                                  help="set status on pre-Plan-09 rows")
    ext_back.add_argument("--iou-gate", type=float, default=0.90)
```

And add command handlers:

```python
def _cmd_extract_auto(args: argparse.Namespace) -> int:
    from olik_font.bulk.batch import run_batch
    from olik_font.sink.connection import connect
    from olik_font.sink.schema import ensure_schema

    db = connect()
    ensure_schema(db)
    report = run_batch(
        db=db,
        count=args.count, seed=args.seed,
        iou_gate=args.iou_gate, cap=args.max_variants_per_proto,
        dry_run=args.dry_run,
    )
    print(f"selected {report.selected} buckets (seed={report.seed})")
    for s, n in report.counts.items():
        print(f"  {s.value:20s} {n}")
    return 0


def _cmd_extract_report(args: argparse.Namespace) -> int:
    from olik_font.bulk.charlist import load_moe_4808
    from olik_font.sink.connection import connect
    from olik_font.sink.schema import ensure_schema

    db = connect()
    ensure_schema(db)
    total_pool = len(load_moe_4808())
    filled = db.query("SELECT count() FROM glyph GROUP ALL;")[0]["result"]
    n_filled = filled[0]["count"] if filled else 0
    print(f"filled {n_filled} / {total_pool}")

    rows = db.query(
        "SELECT status, count() FROM glyph GROUP BY status ORDER BY status;"
    )[0]["result"]
    for r in rows:
        print(f"  {(r.get('status') or '(none)'):20s} {r['count']}")

    ops = db.query(
        "SELECT missing_op, count() FROM glyph "
        "WHERE status = 'unsupported_op' GROUP BY missing_op;"
    )[0]["result"]
    if ops:
        print("unsupported-op histogram:")
        for r in ops:
            print(f"  {r['missing_op']:10s} {r['count']}")
    return 0


def _cmd_extract_backfill(args: argparse.Namespace) -> int:
    from olik_font.sink.connection import connect
    from olik_font.sink.schema import ensure_schema

    db = connect()
    ensure_schema(db)
    gate = args.iou_gate
    db.query(
        "UPDATE glyph SET status = 'verified' "
        "WHERE (status = NONE OR status = '') AND iou_mean >= $g;",
        {"g": gate},
    )
    db.query(
        "UPDATE glyph SET status = 'needs_review' "
        "WHERE (status = NONE OR status = '') AND iou_mean < $g AND iou_mean > 0;",
        {"g": gate},
    )
    return 0
```

And in `main()`:

```python
    if args.cmd == "extract":
        if args.ext_cmd == "auto":              return _cmd_extract_auto(args)
        if args.ext_cmd == "report":            return _cmd_extract_report(args)
        if args.ext_cmd == "backfill-status":   return _cmd_extract_backfill(args)
        if args.ext_cmd == "list":              return _cmd_extract_list(args)    # Task 8
        if args.ext_cmd == "retry":             return _cmd_extract_retry(args)   # Task 8
```

- [ ] **Step 4: Run — first three tests must pass**

```bash
.venv/bin/pytest tests/test_cli_extract.py::test_extract_auto_populates_buckets tests/test_cli_extract.py::test_extract_report_prints_counts tests/test_cli_extract.py::test_extract_backfill_marks_seed_glyph_verified -v
```

Expected: 3 passed. The two remaining tests (list, retry) from Task 8 will stay failing until Task 8 lands.

- [ ] **Step 5: Commit**

```bash
git add project/py/src/olik_font/cli.py project/py/tests/test_cli_extract.py
git commit -m "feat(cli): olik extract auto + report + backfill-status"
```

---

## Task 8: CLI `olik extract list` + `olik extract retry`

**Files:**
- Modify: `project/py/src/olik_font/cli.py`
- Modify: `project/py/tests/test_cli_extract.py` (append tests)

- [ ] **Step 1: Append failing tests to `test_cli_extract.py`**

```python
def test_extract_list_prints_chars(
    surreal_ephemeral: DbConfig, monkeypatch: pytest.MonkeyPatch, capsys,
) -> None:
    _set_env(monkeypatch, surreal_ephemeral)
    monkeypatch.setattr("sys.argv", ["olik", "extract", "auto", "--count", "5", "--seed", "0"])
    main()
    monkeypatch.setattr("sys.argv", ["olik", "extract", "list", "--status", "needs_review"])
    rc = main()
    assert rc == 0
    out = capsys.readouterr().out
    # output is one-char-per-line; may be empty if all 5 chose verified,
    # which is fine — we only assert the command exits 0.


def test_extract_retry_updates_status(
    surreal_ephemeral: DbConfig, monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_env(monkeypatch, surreal_ephemeral)
    db = connect(surreal_ephemeral)
    from olik_font.sink.schema import ensure_schema
    ensure_schema(db)
    db.query(
        "UPDATE type::thing('glyph', '明') MERGE "
        "{ char: '明', status: 'unsupported_op', missing_op: 'wb' };"
    )
    monkeypatch.setattr("sys.argv", ["olik", "extract", "retry",
                                    "--status", "unsupported_op"])
    rc = main()
    assert rc == 0
    row = db.query("SELECT status, missing_op FROM glyph WHERE char = '明';")[0]["result"][0]
    # After retry, 明 should either be verified / needs_review (op 'a' is supported)
    assert row["status"] in {"verified", "needs_review"}
    assert row.get("missing_op") in (None, "")
```

- [ ] **Step 2: Run — must fail**

```bash
.venv/bin/pytest tests/test_cli_extract.py::test_extract_list_prints_chars tests/test_cli_extract.py::test_extract_retry_updates_status -v
```

Expected: 2 failed (subcommands not wired).

- [ ] **Step 3: Add argparse wiring in `cli.py`**

Append to the `extract` subparser block:

```python
    ext_list = ext_sub.add_parser("list", help="print chars in a status bucket")
    ext_list.add_argument("--status", required=True,
                          choices=["verified", "needs_review",
                                   "unsupported_op", "failed_extraction"])
    ext_list.add_argument("--limit", type=int, default=50)

    ext_retry = ext_sub.add_parser("retry", help="re-extract chars in a status bucket")
    ext_retry.add_argument("--status", required=True,
                           choices=["unsupported_op", "needs_review",
                                    "failed_extraction"])
    ext_retry.add_argument("--iou-gate", type=float, default=0.90)
    ext_retry.add_argument("--max-variants-per-proto", type=int, default=2)
```

- [ ] **Step 4: Implement handlers**

Append to `cli.py`:

```python
def _cmd_extract_list(args: argparse.Namespace) -> int:
    from olik_font.sink.connection import connect
    from olik_font.sink.schema import ensure_schema

    db = connect(); ensure_schema(db)
    rows = db.query(
        "SELECT char, iou_mean, missing_op, extraction_error "
        "FROM glyph WHERE status = $s ORDER BY char LIMIT $n;",
        {"s": args.status, "n": args.limit},
    )[0]["result"]
    for r in rows:
        extra = ""
        if args.status == "unsupported_op" and r.get("missing_op"):
            extra = f"  ({r['missing_op']})"
        elif args.status == "failed_extraction" and r.get("extraction_error"):
            extra = f"  ({r['extraction_error']})"
        elif args.status == "needs_review" and r.get("iou_mean") is not None:
            extra = f"  (iou={r['iou_mean']:.3f})"
        print(f"{r['char']}{extra}")
    return 0


def _cmd_extract_retry(args: argparse.Namespace) -> int:
    from olik_font.bulk.batch import run_batch
    from olik_font.sink.connection import connect
    from olik_font.sink.schema import ensure_schema

    db = connect(); ensure_schema(db)
    # Get the chars to re-try then clear them from the filled set so
    # run_batch will re-pick them up.
    rows = db.query(
        "SELECT char FROM glyph WHERE status = $s;",
        {"s": args.status},
    )[0]["result"]
    chars = [r["char"] for r in rows]
    if not chars:
        print(f"no chars with status = {args.status}")
        return 0
    for ch in chars:
        db.query("DELETE FROM glyph WHERE char = $c;", {"c": ch})

    # Make run_batch pick exactly this set.
    from olik_font.bulk import charlist as cl
    orig_pool = cl.load_moe_4808
    cl.load_moe_4808 = lambda path=None: chars  # monkey-patched for this call
    try:
        report = run_batch(
            db=db, count=len(chars),
            seed=0, iou_gate=args.iou_gate,
            cap=args.max_variants_per_proto,
        )
    finally:
        cl.load_moe_4808 = orig_pool

    print(f"retried {report.selected} chars")
    for s, n in report.counts.items():
        print(f"  {s.value:20s} {n}")
    return 0
```

- [ ] **Step 5: Re-run full CLI suite — must pass**

```bash
.venv/bin/pytest tests/test_cli_extract.py -v
```

Expected: 5 passed.

- [ ] **Step 6: Commit**

```bash
git add project/py/src/olik_font/cli.py project/py/tests/test_cli_extract.py
git commit -m "feat(cli): olik extract list + retry"
```

---

## Task 9: Taskfile lane + final verification + tag

**Files:**
- Modify: `Taskfile.yml`
- Modify: `vault/plans/2026-04-21-09-bulk-extraction.md` (status → complete)

- [ ] **Step 1: Append extract lanes to `Taskfile.yml`**

```yaml
  extract:batch-100:
    desc: Auto-extract 100 random empty buckets (smoke run)
    cmds:
      - "{{.VENV}}/bin/olik extract auto --count 100 --seed 42"

  extract:batch-500:
    desc: Auto-extract 500 random empty buckets (Plan 09 target)
    cmds:
      - "{{.VENV}}/bin/olik extract auto --count 500 --seed 42"

  extract:report:
    desc: Print status breakdown
    cmds:
      - "{{.VENV}}/bin/olik extract report"

  extract:backfill:
    desc: Set status on pre-Plan-09 rows (one-shot after first deploy)
    cmds:
      - "{{.VENV}}/bin/olik extract backfill-status --iou-gate 0.90"
```

- [ ] **Step 2: Full test run**

```bash
cd project/py && .venv/bin/pytest -q 2>&1 | tail -10
```

Expected: all prior + new tests pass (plus the known 國 xfail).

- [ ] **Step 3: Update plan status frontmatter**

Edit `vault/plans/2026-04-21-09-bulk-extraction.md` — change `status: draft` → `status: complete` in the frontmatter, nothing else.

- [ ] **Step 4: Tag + commit**

```bash
git add Taskfile.yml vault/plans/2026-04-21-09-bulk-extraction.md
git commit -m "chore(bulk): Taskfile extract:* lanes + plan-09 status=complete"
git tag -a plan-09-bulk-extraction \
  -m "Plan 09 complete — bulk extraction pipeline (first 500-char target)"
```

---

## Self-review checklist (for the engineer before merging)

- [ ] All 9 tasks committed in order with the commit messages spelled above.
- [ ] `pytest -q` in `project/py/` green; new `test_bulk_*` + `test_cli_extract` suites all pass.
- [ ] `olik extract auto --count 10 --seed 0 --dry-run` prints a 10-bucket plan without writing to the DB.
- [ ] `olik extract auto --count 10 --seed 0` writes 10 glyph rows with non-NONE `status`.
- [ ] `olik extract report` shows status counts matching row counts in the DB.
- [ ] `olik extract retry --status unsupported_op` exits 0 even when there are no such rows.
- [ ] `plan-09-bulk-extraction` tag present.

## Known limitations (captured for Plan 09.x / Plan 10)

- **Speculative probe_iou**: `run_batch` uses `_trivial_probe_iou` that always returns 1.0 (canonical "fits"). Real IoU is only measured *after* compose/emit, at which point the glyph lands in `verified` or `needs_review` as appropriate. Tightening this (composing against canonical first, checking IoU, then deciding whether to create a variant) is a Plan 09.x polish — the current behavior still produces correct bucket statuses, it just over-reuses canonicals for chars where a variant would have been slightly better. Variant creation still happens when a variant already exists for the context (the idx.variants_of hit).
- **Rules + rule_trace aren't re-synced** by `run_batch`. The 4 seed rule rows from Plan 08 stay. Plan 10's UI doesn't need traces to surface the status queue; a Plan-09.x or Plan-10.x can fold them in.
- **Non-contiguous MMH stroke order** (國-class) still lands in `needs_review` — expected, captured by the IoU gate.
- **Variant naming uses `context_char` directly** (e.g. `proto:tree_in_林`). For non-ASCII chars in the ID this is fine for Surreal (record IDs accept unicode) but queries that embed the ID must quote with backticks.

## Follow-ups for later plans

- **Plan 09.x**: speculative probe — actually compose against canonical first, measure IoU, then decide. Would reduce unnecessary canonical writes at the cost of ~2× compose-time.
- **Plan 10**: Refine / react-admin shell over `@olik/glyph-db` with a `status` filter as the primary navigation axis. First real consumer of the needs_review queue.
- **Plan 11**: ComfyUI MVP — still untouched; `style_variant` + `comfyui_job` stay empty.
- **Plan 12**: coverage expansion — revisit `unsupported_op` bucket, add more ops to the LUT, rerun `olik extract retry`.

## Adjustments after execution

_Notes on LUT surprises (unexpected op frequencies), prototype-id slug collisions, MMH stroke-count mismatches, or test-harness flakiness found during implementation._
