---
title: "Plan 08 — SurrealDB foundation"
created: 2026-04-21
tags: [type/plan, topic/scene-graph, topic/surrealdb]
source: self
spec: "[[2026-04-21-surrealdb-foundation-design]]"
status: draft
phase: 8
depends-on:
  - "[[2026-04-21-03-python-compose-cli]]"
  - "[[2026-04-21-04-ts-foundation]]"
---

# Plan 08 — SurrealDB Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace static JSON as the source of truth for glyph data with a running SurrealDB instance (`hanfont/olik` on `127.0.0.1:6480`), expose a Python sink (`olik db sync|export|reset`) for ingest + egress, and ship a typed TS client package (`@olik/glyph-db`) with LIVE-query plumbing for Plan 11 ComfyUI variant streaming. Migrate the existing 4 seed records in as a smoke test.

**Architecture:** Hybrid schema — graph edges (`glyph->uses->prototype`, `glyph->cites->rule`) for cross-glyph queries + embedded fields (stroke geometry, layout tree, render layers) for per-glyph detail. Tables are SCHEMALESS with explicit indexes on query-relevant columns; validation stays in Pydantic / Zod layers on either side of the DB. Python uses HTTP transport, TS uses WebSocket for LIVE subscriptions.

**Tech Stack:** SurrealDB 3.0.4 (surrealkv backend), `surrealdb` pypi package, `surrealdb` npm package (v1.x — wraps Surreal 3 protocol), Python 3.11+, TypeScript 5.6, vitest, pytest.

---

## File Structure

```
project/py/
├── pyproject.toml                                     # + surrealdb dep
├── src/olik_font/
│   ├── cli.py                                         # + "db" subcommand tree
│   └── sink/
│       ├── __init__.py
│       ├── connection.py                              # env → Surreal() factory
│       ├── schema.py                                  # DDL + ensure_schema()
│       └── surrealdb.py                               # upsert_* + clear_* helpers
└── tests/
    ├── conftest.py                                    # + surreal_ephemeral fixture
    ├── test_sink_connection.py                        # env override + defaults
    ├── test_sink_schema.py                            # ensure_schema idempotent
    ├── test_sink_upsert_prototype.py                  # prototype idempotency
    ├── test_sink_upsert_glyph.py                      # glyph + uses edges
    ├── test_sink_upsert_rules.py                      # rule + cites edges
    └── test_cli_db.py                                 # sync/export/reset CLI

project/ts/
├── packages/glyph-db/
│   ├── package.json
│   ├── tsconfig.json
│   ├── tsup.config.ts
│   ├── vitest.config.ts
│   ├── src/
│   │   ├── index.ts                                   # re-exports
│   │   ├── client.ts                                  # createDb + OlikDb
│   │   ├── queries.ts                                 # list/get helpers
│   │   └── types.ts                                   # GlyphSummary etc.
│   └── test/
│       ├── helpers.ts                                 # spawn surreal memory per suite
│       ├── contract.test.ts                           # sync → query roundtrip
│       ├── queries.test.ts                            # filter/sort/paginate
│       └── live.test.ts                               # subscribeVariants
└── pnpm-lock.yaml                                     # regenerated

Taskfile.yml                                           # + db:up/down/reset/seed/export
```

Rules: any task that changes Python dependencies must rerun `pip install -e .[dev]` in the workflow harness so the new module resolves; any task that adds a TS workspace package must be followed by `pnpm install --frozen-lockfile=false` at `project/ts/`.

---

## Task 1: Python deps, connection module, DDL + `ensure_schema`

**Files:**
- Modify: `project/py/pyproject.toml`
- Create: `project/py/src/olik_font/sink/__init__.py`
- Create: `project/py/src/olik_font/sink/connection.py`
- Create: `project/py/src/olik_font/sink/schema.py`
- Modify: `project/py/tests/conftest.py`
- Create: `project/py/tests/test_sink_connection.py`
- Create: `project/py/tests/test_sink_schema.py`

- [ ] **Step 1: Add `surrealdb` dep to pyproject.toml**

Inside the existing `[project] dependencies` list, append `"surrealdb>=1.0,<2.0"`. Keep alphabetical where possible. Then:

```bash
cd project/py && .venv/bin/pip install -e .[dev]
```

Expected: `Successfully installed surrealdb-<version>`.

- [ ] **Step 2: `sink/__init__.py`** (exports)

```python
# project/py/src/olik_font/sink/__init__.py
"""SurrealDB sink for glyph records."""

from olik_font.sink.connection import connect
from olik_font.sink.schema import DDL, ensure_schema

__all__ = ["connect", "DDL", "ensure_schema"]
```

- [ ] **Step 3: `sink/connection.py`**

```python
# project/py/src/olik_font/sink/connection.py
"""Connection factory — reads OLIK_DB_* env vars with sensible defaults."""

from __future__ import annotations

import os
from dataclasses import dataclass

from surrealdb import Surreal


@dataclass(frozen=True)
class DbConfig:
    url: str
    namespace: str
    database: str
    user: str
    password: str

    @classmethod
    def from_env(cls) -> "DbConfig":
        return cls(
            url=os.environ.get("OLIK_DB_URL", "http://127.0.0.1:6480"),
            namespace=os.environ.get("OLIK_DB_NS", "hanfont"),
            database=os.environ.get("OLIK_DB_NAME", "olik"),
            user=os.environ.get("OLIK_DB_USER", "root"),
            password=os.environ.get("OLIK_DB_PASS", "root"),
        )


def connect(config: DbConfig | None = None) -> Surreal:
    """Open a SurrealDB connection, sign in, select NS/DB."""
    cfg = config or DbConfig.from_env()
    db = Surreal(cfg.url)
    db.signin({"username": cfg.user, "password": cfg.password})
    db.use(cfg.namespace, cfg.database)
    return db
```

- [ ] **Step 4: `sink/schema.py`**

```python
# project/py/src/olik_font/sink/schema.py
"""DDL for the olik SurrealDB schema + `ensure_schema`."""

from __future__ import annotations

from surrealdb import Surreal


DDL = """
-- glyph: one row per character, embedded stroke/layout data
DEFINE TABLE glyph SCHEMALESS;
DEFINE INDEX glyph_char_uniq ON glyph FIELDS char UNIQUE;
DEFINE INDEX glyph_stroke_ct ON glyph FIELDS stroke_count;
DEFINE INDEX glyph_radical   ON glyph FIELDS radical;
DEFINE INDEX glyph_iou_mean  ON glyph FIELDS iou_mean;

-- prototype: reusable component, referenced by glyphs via `uses` edges
DEFINE TABLE prototype SCHEMALESS;
DEFINE INDEX proto_id_uniq ON prototype FIELDS id UNIQUE;
DEFINE INDEX proto_name    ON prototype FIELDS name;

-- rule: one row per decomposition/placement rule
DEFINE TABLE rule SCHEMALESS;
DEFINE INDEX rule_id_uniq ON rule FIELDS id UNIQUE;
DEFINE INDEX rule_bucket  ON rule FIELDS bucket;

-- rule_trace: per-glyph log of fired rules (append-only)
DEFINE TABLE rule_trace SCHEMALESS;
DEFINE INDEX rt_glyph_order ON rule_trace FIELDS glyph, order;

-- extraction_run: provenance of `olik db sync` invocations
DEFINE TABLE extraction_run SCHEMALESS;

-- style_variant: ComfyUI-produced variants (Plan 11 fills this).
-- Keyed on (char, style_name) — no record-link to glyph for simplicity;
-- char is denormalised here so LIVE queries can filter cheaply.
DEFINE TABLE style_variant SCHEMALESS;
DEFINE INDEX sv_char_style ON style_variant FIELDS char, style_name UNIQUE;

-- comfyui_job: job tracking (Plan 11 fills this)
DEFINE TABLE comfyui_job SCHEMALESS;
DEFINE INDEX cj_id_uniq ON comfyui_job FIELDS id UNIQUE;

-- Edge tables (auto-created by RELATE, but pinned to catch typos)
DEFINE TABLE uses  SCHEMALESS;
DEFINE TABLE cites SCHEMALESS;
"""


def ensure_schema(db: Surreal) -> None:
    """Apply DDL. DEFINE statements are overwrite-safe so this is idempotent."""
    db.query(DDL)
```

- [ ] **Step 5: `conftest.py` — ephemeral SurrealDB fixture**

Add to `project/py/tests/conftest.py` (create if missing; otherwise append):

```python
# project/py/tests/conftest.py
"""Shared test fixtures."""

from __future__ import annotations

import os
import socket
import subprocess
import time
from collections.abc import Generator

import pytest

from olik_font.sink.connection import DbConfig, connect


def _pick_port() -> int:
    """Reserve a free TCP port by binding then closing."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="session")
def surreal_ephemeral() -> Generator[DbConfig, None, None]:
    """Start an in-memory SurrealDB on a random port for the test session."""
    port = _pick_port()
    proc = subprocess.Popen(
        [
            "surreal", "start",
            "--user", "root", "--pass", "root",
            "--bind", f"127.0.0.1:{port}",
            "memory",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    # Wait up to 10s for the HTTP server to answer.
    cfg = DbConfig(
        url=f"http://127.0.0.1:{port}",
        namespace="hanfont",
        database="olik_test",
        user="root",
        password="root",
    )
    deadline = time.time() + 10
    while time.time() < deadline:
        try:
            db = connect(cfg)
            db.close()
            break
        except Exception:
            time.sleep(0.1)
    else:
        proc.terminate()
        raise RuntimeError("ephemeral surrealdb did not become reachable")

    try:
        yield cfg
    finally:
        proc.terminate()
        proc.wait(timeout=5)
```

- [ ] **Step 6: Write failing tests**

```python
# project/py/tests/test_sink_connection.py
"""Connection factory reads env vars correctly."""

from __future__ import annotations

import os

import pytest

from olik_font.sink.connection import DbConfig


def test_from_env_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in ("OLIK_DB_URL", "OLIK_DB_NS", "OLIK_DB_NAME", "OLIK_DB_USER", "OLIK_DB_PASS"):
        monkeypatch.delenv(var, raising=False)
    cfg = DbConfig.from_env()
    assert cfg.url       == "http://127.0.0.1:6480"
    assert cfg.namespace == "hanfont"
    assert cfg.database  == "olik"
    assert cfg.user      == "root"
    assert cfg.password  == "root"


def test_from_env_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OLIK_DB_URL",  "http://example:9999")
    monkeypatch.setenv("OLIK_DB_NS",   "other_ns")
    monkeypatch.setenv("OLIK_DB_NAME", "other_db")
    cfg = DbConfig.from_env()
    assert cfg.url       == "http://example:9999"
    assert cfg.namespace == "other_ns"
    assert cfg.database  == "other_db"
```

```python
# project/py/tests/test_sink_schema.py
"""ensure_schema is idempotent and creates the expected tables."""

from __future__ import annotations

import pytest

from olik_font.sink.connection import DbConfig, connect
from olik_font.sink.schema import ensure_schema


EXPECTED_TABLES = {
    "glyph", "prototype", "rule", "rule_trace",
    "extraction_run", "style_variant", "comfyui_job",
    "uses", "cites",
}


def test_ensure_schema_creates_tables(surreal_ephemeral: DbConfig) -> None:
    db = connect(surreal_ephemeral)
    ensure_schema(db)
    info = db.query("INFO FOR DB;")
    tables = set(info[0]["result"]["tables"].keys())
    missing = EXPECTED_TABLES - tables
    assert missing == set(), f"missing tables: {missing}"


def test_ensure_schema_idempotent(surreal_ephemeral: DbConfig) -> None:
    db = connect(surreal_ephemeral)
    ensure_schema(db)
    ensure_schema(db)  # second call must not raise
    info = db.query("INFO FOR DB;")
    tables = set(info[0]["result"]["tables"].keys())
    assert EXPECTED_TABLES <= tables
```

- [ ] **Step 7: Run tests — must pass**

```bash
cd project/py && .venv/bin/pytest tests/test_sink_connection.py tests/test_sink_schema.py -v
```

Expected: 4 passed.

- [ ] **Step 8: Commit**

```bash
git add project/py/pyproject.toml project/py/src/olik_font/sink/ project/py/tests/conftest.py project/py/tests/test_sink_connection.py project/py/tests/test_sink_schema.py
git commit -m "feat(sink): SurrealDB connection factory + schema DDL"
```

---

## Task 2: `upsert_prototype` — idempotent

**Files:**
- Create: `project/py/src/olik_font/sink/surrealdb.py`
- Create: `project/py/tests/test_sink_upsert_prototype.py`

- [ ] **Step 1: Write failing test first**

```python
# project/py/tests/test_sink_upsert_prototype.py
"""upsert_prototype is idempotent and stores the expected shape."""

from __future__ import annotations

from olik_font.sink.connection import DbConfig, connect
from olik_font.sink.schema import ensure_schema
from olik_font.sink.surrealdb import upsert_prototype


SAMPLE = {
    "id": "proto:moon",
    "name": "moon",
    "source": "extracted from 明",
    "strokes": [{"id": "s0", "path": "M 0 0 L 1 1"}],
}


def test_upsert_prototype_single(surreal_ephemeral: DbConfig) -> None:
    db = connect(surreal_ephemeral)
    ensure_schema(db)
    upsert_prototype(db, SAMPLE)
    rows = db.query("SELECT id, name FROM prototype;")[0]["result"]
    assert len(rows) == 1
    assert rows[0]["id"]   == "proto:moon"
    assert rows[0]["name"] == "moon"


def test_upsert_prototype_idempotent(surreal_ephemeral: DbConfig) -> None:
    db = connect(surreal_ephemeral)
    ensure_schema(db)
    # Call twice with the same id; expect one row.
    upsert_prototype(db, SAMPLE)
    upsert_prototype(db, {**SAMPLE, "name": "moon_updated"})
    rows = db.query("SELECT id, name FROM prototype;")[0]["result"]
    assert len(rows) == 1
    assert rows[0]["name"] == "moon_updated"
```

- [ ] **Step 2: Run to verify it fails**

```bash
.venv/bin/pytest tests/test_sink_upsert_prototype.py -v
```

Expected: `ImportError` on `from olik_font.sink.surrealdb import upsert_prototype`.

- [ ] **Step 3: Implement `sink/surrealdb.py`**

```python
# project/py/src/olik_font/sink/surrealdb.py
"""Write-side helpers — upserts + RELATE wiring."""

from __future__ import annotations

from typing import Any

from surrealdb import Surreal


def _slug_id(raw: str) -> str:
    """Quote a Surreal record-ID component so unicode chars and colons are safe.

    Surreal's `type::thing(table, id)` takes the id as a value; passing the raw
    string through a parameter handles escaping for us.
    """
    return raw


def upsert_prototype(db: Surreal, proto: dict[str, Any]) -> None:
    """Create-or-replace a prototype row keyed on `proto["id"]`."""
    db.query(
        "UPDATE type::thing('prototype', $key) MERGE $data;",
        {"key": _slug_id(proto["id"]), "data": proto},
    )
```

- [ ] **Step 4: Re-run tests, expect pass**

```bash
.venv/bin/pytest tests/test_sink_upsert_prototype.py -v
```

Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add project/py/src/olik_font/sink/surrealdb.py project/py/tests/test_sink_upsert_prototype.py
git commit -m "feat(sink): upsert_prototype with idempotent MERGE semantics"
```

---

## Task 3: `upsert_glyph` + `uses` edges

**Files:**
- Modify: `project/py/src/olik_font/sink/surrealdb.py`
- Create: `project/py/tests/test_sink_upsert_glyph.py`

- [ ] **Step 1: Write failing test**

```python
# project/py/tests/test_sink_upsert_glyph.py
"""upsert_glyph writes a glyph row and wires `uses` edges."""

from __future__ import annotations

from olik_font.sink.connection import DbConfig, connect
from olik_font.sink.schema import ensure_schema
from olik_font.sink.surrealdb import upsert_glyph, upsert_prototype


SAMPLE_PROTO = {
    "id": "proto:moon",
    "name": "moon",
    "source": "extracted from 明",
    "strokes": [],
}

SAMPLE_RECORD = {
    "char": "明",
    "stroke_count": 8,
    "radical": "日",
    "iou_mean": 1.0,
    "stroke_instances":    [{"id": "s0"}, {"id": "s1"}],
    "layout_tree":         {"id": "明", "mode": "left_right", "children": []},
    "render_layers":       [],
    "iou_report":          {"mean": 1.0, "per_group": {}},
    "component_instances": [
        {"id": "inst1", "prototype_ref": "proto:moon", "position": "right",
         "placed_bbox": [0, 0, 1, 1]},
    ],
}


def test_upsert_glyph_row_and_edges(surreal_ephemeral: DbConfig) -> None:
    db = connect(surreal_ephemeral)
    ensure_schema(db)
    upsert_prototype(db, SAMPLE_PROTO)
    upsert_glyph(db, SAMPLE_RECORD)

    rows = db.query("SELECT char, stroke_count, radical, iou_mean FROM glyph;")[0]["result"]
    assert rows == [{"char": "明", "stroke_count": 8, "radical": "日", "iou_mean": 1.0}]

    edges = db.query(
        "SELECT instance_id, position FROM uses WHERE "
        "in = type::thing('glyph', '明');"
    )[0]["result"]
    assert edges == [{"instance_id": "inst1", "position": "right"}]


def test_upsert_glyph_edges_rebuilt_on_resync(surreal_ephemeral: DbConfig) -> None:
    db = connect(surreal_ephemeral)
    ensure_schema(db)
    upsert_prototype(db, SAMPLE_PROTO)
    upsert_glyph(db, SAMPLE_RECORD)

    # Re-sync with zero component_instances — existing edges must vanish.
    upsert_glyph(db, {**SAMPLE_RECORD, "component_instances": []})
    edges = db.query(
        "SELECT * FROM uses WHERE in = type::thing('glyph', '明');"
    )[0]["result"]
    assert edges == []
```

- [ ] **Step 2: Confirm it fails**

```bash
.venv/bin/pytest tests/test_sink_upsert_glyph.py -v
```

Expected: `ImportError: cannot import name 'upsert_glyph'`.

- [ ] **Step 3: Implement `upsert_glyph`**

Append to `project/py/src/olik_font/sink/surrealdb.py`:

```python
def upsert_glyph(db: Surreal, record: dict[str, Any]) -> None:
    """Create-or-replace a glyph + rebuild its `uses` edges from
    `component_instances`.

    Edges are DELETEd-then-RELATEd within a single transaction so a re-sync
    with different component_instances leaves no stale edges.
    """
    char = record["char"]

    # Strip the component_instances out of the embedded glyph row — they're
    # represented as edges, not a field.
    body = {k: v for k, v in record.items() if k != "component_instances"}

    db.query(
        "BEGIN TRANSACTION;"
        "UPDATE type::thing('glyph', $char) MERGE $data;"
        "DELETE uses WHERE in = type::thing('glyph', $char);"
        "COMMIT TRANSACTION;",
        {"char": char, "data": body},
    )

    for inst in record.get("component_instances", []):
        db.query(
            "RELATE type::thing('glyph', $char)->uses->type::thing('prototype', $proto) "
            "CONTENT $edge;",
            {
                "char":  char,
                "proto": inst["prototype_ref"],
                "edge": {
                    "instance_id": inst["id"],
                    "position":    inst.get("position"),
                    "placed_bbox": inst.get("placed_bbox"),
                },
            },
        )
```

- [ ] **Step 4: Re-run tests — all pass**

```bash
.venv/bin/pytest tests/test_sink_upsert_glyph.py -v
```

Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add project/py/src/olik_font/sink/surrealdb.py project/py/tests/test_sink_upsert_glyph.py
git commit -m "feat(sink): upsert_glyph + uses edges with rebuild-on-resync"
```

---

## Task 4: `upsert_rules` + `cites` edges + rule_trace rows

**Files:**
- Modify: `project/py/src/olik_font/sink/surrealdb.py`
- Create: `project/py/tests/test_sink_upsert_rules.py`

- [ ] **Step 1: Write failing test**

```python
# project/py/tests/test_sink_upsert_rules.py
"""upsert_rules stores rules + rule_trace + cites edges."""

from __future__ import annotations

from olik_font.sink.connection import DbConfig, connect
from olik_font.sink.schema import ensure_schema
from olik_font.sink.surrealdb import (
    upsert_glyph, upsert_rules, upsert_rule_trace,
)


BASIC_GLYPH = {
    "char": "明",
    "stroke_count": 8,
    "radical": "日",
    "iou_mean": 1.0,
    "stroke_instances":    [],
    "layout_tree":         {},
    "render_layers":       [],
    "iou_report":          {},
    "component_instances": [],
}

RULES = [
    {"id": "rule:left_right_day",  "pattern": "日+X",    "bucket": "decomp", "resolution": "left_right"},
    {"id": "rule:left_right_moon", "pattern": "X+月",    "bucket": "decomp", "resolution": "left_right"},
]

TRACE = [
    {"rule_id": "rule:left_right_day",  "fired": True,  "order": 0, "alternative": False},
    {"rule_id": "rule:left_right_moon", "fired": False, "order": 1, "alternative": True},
]


def test_upsert_rules_and_trace(surreal_ephemeral: DbConfig) -> None:
    db = connect(surreal_ephemeral)
    ensure_schema(db)

    upsert_rules(db, RULES)
    upsert_glyph(db, BASIC_GLYPH)
    upsert_rule_trace(db, "明", TRACE)

    rule_rows = db.query("SELECT id, pattern, bucket FROM rule ORDER BY id;")[0]["result"]
    assert len(rule_rows) == 2

    trace_rows = db.query(
        "SELECT fired, order FROM rule_trace "
        "WHERE glyph = type::thing('glyph', '明') ORDER BY order;"
    )[0]["result"]
    assert trace_rows == [
        {"fired": True,  "order": 0},
        {"fired": False, "order": 1},
    ]

    cites = db.query(
        "SELECT alternative FROM cites WHERE in = type::thing('glyph', '明') "
        "ORDER BY order;"
    )[0]["result"]
    assert cites == [
        {"alternative": False},
        {"alternative": True},
    ]
```

- [ ] **Step 2: Verify fail**

```bash
.venv/bin/pytest tests/test_sink_upsert_rules.py -v
```

Expected: ImportError on `upsert_rules` / `upsert_rule_trace`.

- [ ] **Step 3: Implement**

Append to `project/py/src/olik_font/sink/surrealdb.py`:

```python
def upsert_rules(db: Surreal, rules: list[dict[str, Any]]) -> None:
    """Idempotent write of the rule catalog."""
    for r in rules:
        db.query(
            "UPDATE type::thing('rule', $key) MERGE $data;",
            {"key": r["id"], "data": r},
        )


def upsert_rule_trace(
    db: Surreal,
    glyph_char: str,
    trace: list[dict[str, Any]],
) -> None:
    """Rewrite the rule_trace log + `cites` edges for one glyph.

    Called once per `olik db sync` invocation per glyph; entries are deleted
    first so we never accumulate duplicates on re-sync.
    """
    db.query(
        "BEGIN TRANSACTION;"
        "DELETE rule_trace WHERE glyph = type::thing('glyph', $char);"
        "DELETE cites WHERE in = type::thing('glyph', $char);"
        "COMMIT TRANSACTION;",
        {"char": glyph_char},
    )
    for entry in trace:
        db.query(
            "CREATE rule_trace CONTENT $data;",
            {
                "data": {
                    "glyph":       f"glyph:{glyph_char}",
                    "rule":        f"rule:{entry['rule_id']}",
                    "fired":       entry["fired"],
                    "order":       entry["order"],
                    "alternative": entry.get("alternative", False),
                }
            },
        )
        db.query(
            "RELATE type::thing('glyph', $char)->cites->type::thing('rule', $rid) "
            "CONTENT $edge;",
            {
                "char": glyph_char,
                "rid":  entry["rule_id"],
                "edge": {
                    "order":       entry["order"],
                    "alternative": entry.get("alternative", False),
                },
            },
        )
```

- [ ] **Step 4: Re-run — must pass**

```bash
.venv/bin/pytest tests/test_sink_upsert_rules.py -v
```

Expected: 1 passed.

- [ ] **Step 5: Commit**

```bash
git add project/py/src/olik_font/sink/surrealdb.py project/py/tests/test_sink_upsert_rules.py
git commit -m "feat(sink): upsert_rules + rule_trace + cites edges"
```

---

## Task 5: CLI verbs `olik db sync` and `olik db reset`

**Files:**
- Modify: `project/py/src/olik_font/cli.py`
- Create: `project/py/tests/test_cli_db_sync.py`

- [ ] **Step 1: Write failing CLI test**

```python
# project/py/tests/test_cli_db_sync.py
"""`olik db sync 明` populates the DB; `db reset` drops + recreates."""

from __future__ import annotations

import os

import pytest

from olik_font.cli import main
from olik_font.sink.connection import DbConfig, connect


def _set_env(monkeypatch: pytest.MonkeyPatch, cfg: DbConfig) -> None:
    monkeypatch.setenv("OLIK_DB_URL",  cfg.url)
    monkeypatch.setenv("OLIK_DB_NS",   cfg.namespace)
    monkeypatch.setenv("OLIK_DB_NAME", cfg.database)
    monkeypatch.setenv("OLIK_DB_USER", cfg.user)
    monkeypatch.setenv("OLIK_DB_PASS", cfg.password)


def test_db_sync_writes_glyph(
    surreal_ephemeral: DbConfig,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_env(monkeypatch, surreal_ephemeral)
    monkeypatch.setattr("sys.argv", ["olik", "db", "sync", "明"])
    rc = main()
    assert rc == 0

    db = connect(surreal_ephemeral)
    row = db.query("SELECT char, stroke_count FROM glyph WHERE char = '明';")[0]["result"]
    assert len(row) == 1
    assert row[0]["char"] == "明"
    assert row[0]["stroke_count"] >= 1


def test_db_reset_clears_and_recreates(
    surreal_ephemeral: DbConfig,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_env(monkeypatch, surreal_ephemeral)
    # seed one char
    monkeypatch.setattr("sys.argv", ["olik", "db", "sync", "明"])
    main()
    # reset
    monkeypatch.setattr("sys.argv", ["olik", "db", "reset", "--yes"])
    rc = main()
    assert rc == 0
    # DB is back to empty but schema is re-applied
    db = connect(surreal_ephemeral)
    rows = db.query("SELECT * FROM glyph;")[0]["result"]
    assert rows == []
    info = db.query("INFO FOR DB;")[0]["result"]
    assert "glyph" in info["tables"]
```

- [ ] **Step 2: Verify fails**

```bash
.venv/bin/pytest tests/test_cli_db_sync.py -v
```

Expected: exits with `unknown cmd: db` or a `SystemExit(2)` from argparse.

- [ ] **Step 3: Extract build helper + add `db` subtree to `cli.py`**

Replace `project/py/src/olik_font/cli.py` with the expanded version below (keeps the existing `build` command semantics, extracts the record-building pipeline into a reusable helper, and adds the `db` subcommand tree):

```python
"""`olik` CLI: fetch -> extract -> decompose -> compose -> emit / sync."""

from __future__ import annotations

import argparse
import json
import platform
import sys
from pathlib import Path
from typing import Any

import yaml

from olik_font.compose.walk import compose_transforms
from olik_font.decompose.instance import build_instance_tree
from olik_font.emit.library import library_to_dict
from olik_font.emit.record import build_glyph_record
from olik_font.emit.trace import trace_to_dict
from olik_font.prototypes.extract import extract_all_prototypes
from olik_font.prototypes.extraction_plan import load_extraction_plan
from olik_font.rules.engine import apply_first_match, load_rules
from olik_font.sources.makemeahanzi import fetch_mmh, load_mmh_graphics
from olik_font.types import PrototypeLibrary

_PY_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_MMH_DIR = _PY_ROOT / "data" / "mmh"
_DEFAULT_PLAN = _PY_ROOT / "data" / "extraction_plan.yaml"
_DEFAULT_RULES = _PY_ROOT / "src" / "olik_font" / "rules" / "rules.yaml"


# --------------------------------------------------------------------------
# Argument parser
# --------------------------------------------------------------------------

def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="olik")
    subparsers = parser.add_subparsers(dest="cmd", required=True)

    # ---- build (JSON output) ----
    build = subparsers.add_parser("build", help="build glyph records for one or more characters")
    build.add_argument("chars", nargs="+")
    build.add_argument("-o", "--out", required=True, type=Path)
    build.add_argument("--mmh-dir", default=_DEFAULT_MMH_DIR, type=Path)
    build.add_argument("--plan",    default=_DEFAULT_PLAN, type=Path)
    build.add_argument("--rules",   default=_DEFAULT_RULES, type=Path)

    # ---- db (SurrealDB sink) ----
    db = subparsers.add_parser("db", help="SurrealDB sink operations")
    db_sub = db.add_subparsers(dest="db_cmd", required=True)

    db_sync = db_sub.add_parser("sync", help="build + push records into SurrealDB")
    db_sync.add_argument("chars", nargs="+")
    db_sync.add_argument("--mmh-dir", default=_DEFAULT_MMH_DIR, type=Path)
    db_sync.add_argument("--plan",    default=_DEFAULT_PLAN, type=Path)
    db_sync.add_argument("--rules",   default=_DEFAULT_RULES, type=Path)

    db_reset = db_sub.add_parser("reset", help="drop + recreate the olik schema")
    db_reset.add_argument("--yes", action="store_true",
                          help="required — confirms you really want to drop data")

    db_export = db_sub.add_parser("export", help="dump DB back to JSON")
    db_export.add_argument("--out", required=True, type=Path)

    return parser.parse_args(argv)


# --------------------------------------------------------------------------
# Build pipeline (extracted for reuse by `build` + `db sync`)
# --------------------------------------------------------------------------

def _build_artifacts(
    chars: list[str],
    mmh_dir: Path,
    plan_path: Path,
    rules_path: Path,
) -> tuple[dict[str, dict[str, Any]], dict[str, Any], list[dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    """Produce (records_by_char, library_dict, rules_catalog, traces_by_char).

    Reuses the existing build machinery; no side effects on disk.
    """
    graphics = load_mmh_graphics(fetch_mmh(mmh_dir))
    plan = load_extraction_plan(plan_path)
    rules_meta = yaml.safe_load(rules_path.read_text(encoding="utf-8"))
    rules = load_rules(rules_path)

    library: PrototypeLibrary = extract_all_prototypes(plan, graphics)

    records: dict[str, dict[str, Any]] = {}
    traces:  dict[str, list[dict[str, Any]]] = {}

    for ch in chars:
        tree = build_instance_tree(ch, plan, library, graphics)
        composed = compose_transforms(tree, library)
        trace = apply_first_match(ch, tree, rules)
        record = build_glyph_record(ch, composed, library, trace, rules_meta)
        records[ch] = record
        traces[ch]  = [trace_to_dict(t) for t in trace]

    rules_catalog = [
        {"id": r.id, "pattern": r.pattern, "bucket": r.bucket,
         "resolution": r.resolution}
        for r in rules
    ]
    return records, library_to_dict(library), rules_catalog, traces


# --------------------------------------------------------------------------
# Command handlers
# --------------------------------------------------------------------------

def _cmd_build(args: argparse.Namespace) -> int:
    out: Path = args.out
    out.mkdir(parents=True, exist_ok=True)
    records, library, rules_catalog, traces = _build_artifacts(
        args.chars, args.mmh_dir, args.plan, args.rules,
    )
    (out / "prototype-library.json").write_text(
        json.dumps(library, ensure_ascii=False, indent=2), encoding="utf-8",
    )
    (out / "rules.json").write_text(
        json.dumps(rules_catalog, ensure_ascii=False, indent=2), encoding="utf-8",
    )
    for ch, rec in records.items():
        (out / f"glyph-record-{ch}.json").write_text(
            json.dumps(rec, ensure_ascii=False, indent=2), encoding="utf-8",
        )
        (out / f"rule-trace-{ch}.json").write_text(
            json.dumps(traces[ch], ensure_ascii=False, indent=2), encoding="utf-8",
        )
    return 0


def _cmd_db_sync(args: argparse.Namespace) -> int:
    from olik_font.sink.connection import connect
    from olik_font.sink.schema import ensure_schema
    from olik_font.sink.surrealdb import (
        upsert_glyph, upsert_prototype, upsert_rules, upsert_rule_trace,
    )

    records, library, rules_catalog, traces = _build_artifacts(
        args.chars, args.mmh_dir, args.plan, args.rules,
    )

    db = connect()
    ensure_schema(db)

    # prototypes
    for proto_id, proto in library.get("prototypes", {}).items():
        upsert_prototype(db, {"id": proto_id, **proto})

    # rules
    upsert_rules(db, rules_catalog)

    # glyphs + traces
    for ch, rec in records.items():
        upsert_glyph(db, rec)
        upsert_rule_trace(db, ch, traces[ch])

    # provenance (append-only log row)
    db.query(
        "CREATE extraction_run CONTENT $data;",
        {"data": {
            "chars_processed": args.chars,
            "olik_version":    _olik_version(),
            "mmh_dir":         str(args.mmh_dir),
            "plan":            str(args.plan),
            "host":            platform.node(),
        }},
    )
    return 0


def _cmd_db_reset(args: argparse.Namespace) -> int:
    from olik_font.sink.connection import DbConfig, connect
    from olik_font.sink.schema import ensure_schema

    if not args.yes:
        print("refusing to reset without --yes", file=sys.stderr)
        return 2

    cfg = DbConfig.from_env()
    if "127.0.0.1" not in cfg.url and "localhost" not in cfg.url:
        print(f"refusing to reset non-local DB ({cfg.url})", file=sys.stderr)
        return 2

    db = connect(cfg)
    db.query(f"REMOVE DATABASE {cfg.database};")
    db.query(f"DEFINE DATABASE {cfg.database};")
    db.use(cfg.namespace, cfg.database)
    ensure_schema(db)
    return 0


def _cmd_db_export(args: argparse.Namespace) -> int:  # placeholder; filled in Task 6
    raise NotImplementedError("db export — implemented in Task 6")


def _olik_version() -> str:
    try:
        from importlib.metadata import version
        return version("olik-font")
    except Exception:
        return "unknown"


# --------------------------------------------------------------------------
# Entry point
# --------------------------------------------------------------------------

def main() -> int:
    args = _parse_args(sys.argv[1:])
    if args.cmd == "build":
        return _cmd_build(args)
    if args.cmd == "db":
        if args.db_cmd == "sync":
            return _cmd_db_sync(args)
        if args.db_cmd == "reset":
            return _cmd_db_reset(args)
        if args.db_cmd == "export":
            return _cmd_db_export(args)
    print(f"unknown cmd: {args.cmd}", file=sys.stderr)
    return 2
```

- [ ] **Step 4: Re-run — must pass**

```bash
.venv/bin/pytest tests/test_cli_db_sync.py -v
```

Expected: 2 passed. Also re-run prior suite to confirm no regression:

```bash
.venv/bin/pytest tests/ -q
```

Expected: same count as before + 2 new passes.

- [ ] **Step 5: Commit**

```bash
git add project/py/src/olik_font/cli.py project/py/tests/test_cli_db_sync.py
git commit -m "feat(cli): olik db sync + db reset verbs"
```

---

## Task 6: CLI verb `olik db export` (DB → JSON roundtrip)

**Files:**
- Modify: `project/py/src/olik_font/cli.py`
- Create: `project/py/tests/test_cli_db_export.py`

- [ ] **Step 1: Write failing test**

```python
# project/py/tests/test_cli_db_export.py
"""`olik db export` produces a JSON directory matching `olik build`'s shape."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from olik_font.cli import main
from olik_font.sink.connection import DbConfig


def _set_env(monkeypatch: pytest.MonkeyPatch, cfg: DbConfig) -> None:
    for var, val in [
        ("OLIK_DB_URL",  cfg.url),
        ("OLIK_DB_NS",   cfg.namespace),
        ("OLIK_DB_NAME", cfg.database),
        ("OLIK_DB_USER", cfg.user),
        ("OLIK_DB_PASS", cfg.password),
    ]:
        monkeypatch.setenv(var, val)


def test_db_export_produces_json_dir(
    surreal_ephemeral: DbConfig,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _set_env(monkeypatch, surreal_ephemeral)

    monkeypatch.setattr("sys.argv", ["olik", "db", "sync", "明"])
    main()

    out = tmp_path / "export"
    monkeypatch.setattr("sys.argv", ["olik", "db", "export", "--out", str(out)])
    rc = main()
    assert rc == 0

    # Expected filenames present
    assert (out / "prototype-library.json").exists()
    assert (out / "glyph-record-明.json").exists()

    rec = json.loads((out / "glyph-record-明.json").read_text(encoding="utf-8"))
    assert rec["char"] == "明"
    assert "stroke_instances" in rec
```

- [ ] **Step 2: Confirm it fails**

```bash
.venv/bin/pytest tests/test_cli_db_export.py -v
```

Expected: `NotImplementedError: db export — implemented in Task 6`.

- [ ] **Step 3: Implement `_cmd_db_export`**

Replace the `_cmd_db_export` stub in `project/py/src/olik_font/cli.py` with:

```python
def _cmd_db_export(args: argparse.Namespace) -> int:
    from olik_font.sink.connection import connect

    out: Path = args.out
    out.mkdir(parents=True, exist_ok=True)
    db = connect()

    # Prototypes → {prototypes: {id: {...}}}
    proto_rows = db.query("SELECT * FROM prototype;")[0]["result"]
    library = {
        "prototypes": {
            row["id"]: {k: v for k, v in row.items() if k not in {"id"}}
            for row in proto_rows
        }
    }
    (out / "prototype-library.json").write_text(
        json.dumps(library, ensure_ascii=False, indent=2), encoding="utf-8",
    )

    # Rules
    rule_rows = db.query("SELECT id, pattern, bucket, resolution FROM rule;")[0]["result"]
    (out / "rules.json").write_text(
        json.dumps(rule_rows, ensure_ascii=False, indent=2), encoding="utf-8",
    )

    # Glyphs (including their `uses` edges rebuilt as component_instances)
    glyph_rows = db.query("SELECT * FROM glyph;")[0]["result"]
    for g in glyph_rows:
        ch = g["char"]
        edges = db.query(
            "SELECT instance_id, position, placed_bbox, out AS prototype_ref "
            "FROM uses WHERE in = type::thing('glyph', $char);",
            {"char": ch},
        )[0]["result"]
        g["component_instances"] = [
            {
                "id":            e["instance_id"],
                "prototype_ref": str(e["prototype_ref"]).replace("prototype:", ""),
                "position":      e.get("position"),
                "placed_bbox":   e.get("placed_bbox"),
            }
            for e in edges
        ]
        (out / f"glyph-record-{ch}.json").write_text(
            json.dumps(g, ensure_ascii=False, indent=2), encoding="utf-8",
        )

    # Rule traces
    for g in glyph_rows:
        ch = g["char"]
        trace_rows = db.query(
            "SELECT rule, fired, order, alternative FROM rule_trace "
            "WHERE glyph = type::thing('glyph', $char) ORDER BY order;",
            {"char": ch},
        )[0]["result"]
        simple = [
            {
                "rule_id":     str(t["rule"]).replace("rule:", ""),
                "fired":       t["fired"],
                "order":       t["order"],
                "alternative": t.get("alternative", False),
            }
            for t in trace_rows
        ]
        (out / f"rule-trace-{ch}.json").write_text(
            json.dumps(simple, ensure_ascii=False, indent=2), encoding="utf-8",
        )
    return 0
```

- [ ] **Step 4: Re-run tests**

```bash
.venv/bin/pytest tests/test_cli_db_export.py tests/test_cli_db_sync.py -v
```

Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add project/py/src/olik_font/cli.py project/py/tests/test_cli_db_export.py
git commit -m "feat(cli): olik db export reconstructs JSON from DB"
```

---

## Task 7: TS `@olik/glyph-db` scaffold + `createDb` + contract test

**Files:**
- Create: `project/ts/packages/glyph-db/package.json`
- Create: `project/ts/packages/glyph-db/tsconfig.json`
- Create: `project/ts/packages/glyph-db/tsup.config.ts`
- Create: `project/ts/packages/glyph-db/vitest.config.ts`
- Create: `project/ts/packages/glyph-db/src/index.ts`
- Create: `project/ts/packages/glyph-db/src/client.ts`
- Create: `project/ts/packages/glyph-db/src/types.ts`
- Create: `project/ts/packages/glyph-db/test/helpers.ts`
- Create: `project/ts/packages/glyph-db/test/contract.test.ts`

- [ ] **Step 1: `package.json`**

```json
{
  "name": "@olik/glyph-db",
  "version": "0.1.0",
  "private": true,
  "type": "module",
  "main":  "./dist/index.cjs",
  "module":"./dist/index.js",
  "types": "./dist/index.d.ts",
  "exports": {
    ".": {
      "import":  "./dist/index.js",
      "require": "./dist/index.cjs",
      "types":   "./dist/index.d.ts"
    }
  },
  "scripts": {
    "build":     "tsup",
    "test":      "vitest run",
    "typecheck": "tsc --noEmit"
  },
  "dependencies": {
    "@olik/glyph-schema": "workspace:*",
    "surrealdb":          "^1.0.0"
  },
  "devDependencies": {
    "tsup":        "8.3.0",
    "typescript":  "5.6.3",
    "vitest":      "2.1.2"
  }
}
```

- [ ] **Step 2: `tsconfig.json` / `tsup.config.ts` / `vitest.config.ts`**

```json
// tsconfig.json
{
  "extends": "../../tsconfig.base.json",
  "compilerOptions": {
    "composite": false,
    "rootDir": "./src",
    "outDir":  "./dist"
  },
  "include": ["src/**/*"]
}
```

```ts
// tsup.config.ts
import { defineConfig } from "tsup";
export default defineConfig({
  entry:     ["src/index.ts"],
  format:    ["esm", "cjs"],
  dts:       true,
  clean:     true,
  sourcemap: true,
  target:    "es2022",
  external:  ["surrealdb"],
});
```

```ts
// vitest.config.ts
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig } from "vitest/config";

const __dirname = fileURLToPath(new URL(".", import.meta.url));

export default defineConfig({
  resolve: {
    alias: {
      "@olik/glyph-schema": resolve(__dirname, "../glyph-schema/src/index.ts"),
    },
  },
  test: { testTimeout: 30000 },
});
```

- [ ] **Step 3: `src/types.ts`**

```ts
// project/ts/packages/glyph-db/src/types.ts
import type { GlyphRecord, Prototype } from "@olik/glyph-schema";

export interface GlyphSummary {
  char:         string;
  stroke_count: number;
  radical:      string | null;
  iou_mean:     number;
}

export interface PrototypeSummary {
  id:           string;
  name:         string;
  usage_count?: number;
}

export interface StyleVariant {
  char:          string;
  style_name:    string;
  image_ref:     string;
  workflow_id?:  string;
  status:        "queued" | "running" | "done" | "failed";
  generated_at?: string;
}

export type ListFilter = {
  radical?:          string;
  strokeCountRange?: [number, number];
  iouBelow?:         number;
};

export interface ListOpts {
  filter?:   ListFilter;
  sort?:     "char" | "stroke_count" | "iou_mean";
  pageSize?: number;
  cursor?:   string;
}

export interface ListPage<T> {
  items:      T[];
  nextCursor?: string;
}

export type Unsubscribe = () => Promise<void>;

// re-exports for consumers so they don't have to dep on @olik/glyph-schema
export type { GlyphRecord, Prototype };
```

- [ ] **Step 4: `src/client.ts`**

```ts
// project/ts/packages/glyph-db/src/client.ts
import { Surreal } from "surrealdb";

import type { GlyphRecord, Prototype } from "@olik/glyph-schema";
import type {
  GlyphSummary, ListOpts, ListPage, PrototypeSummary,
  StyleVariant, Unsubscribe,
} from "./types.js";

export interface DbConfig {
  url:       string;
  namespace: string;
  database:  string;
  user:      string;
  pass:      string;
}

export const DEFAULT_DB_CONFIG: DbConfig = {
  url:       "ws://127.0.0.1:6480/rpc",
  namespace: "hanfont",
  database:  "olik",
  user:      "root",
  pass:      "root",
};

export interface OlikDb {
  listGlyphs(opts?: ListOpts):             Promise<ListPage<GlyphSummary>>;
  getGlyph(char: string):                   Promise<GlyphRecord | null>;
  listPrototypes():                         Promise<PrototypeSummary[]>;
  getPrototypeUsers(id: string):            Promise<GlyphSummary[]>;
  listVariants(char: string):               Promise<StyleVariant[]>;
  subscribeVariants(
    char: string,
    cb: (v: StyleVariant) => void,
  ):                                        Promise<Unsubscribe>;
  close():                                  Promise<void>;
}

export async function createDb(config: Partial<DbConfig> = {}): Promise<OlikDb> {
  const cfg: DbConfig = { ...DEFAULT_DB_CONFIG, ...config };
  const raw = new Surreal();
  await raw.connect(cfg.url);
  await raw.signin({ username: cfg.user, password: cfg.pass });
  await raw.use({ namespace: cfg.namespace, database: cfg.database });

  // Query helpers are imported lazily to keep this file focused.
  const { makeQueries } = await import("./queries.js");
  return makeQueries(raw);
}
```

- [ ] **Step 5: `src/queries.ts` — minimal stub (filled in Tasks 8-9)**

```ts
// project/ts/packages/glyph-db/src/queries.ts
import type { Surreal } from "surrealdb";

import type {
  GlyphSummary, ListOpts, ListPage, PrototypeSummary, StyleVariant,
} from "./types.js";
import type { GlyphRecord } from "@olik/glyph-schema";
import type { OlikDb } from "./client.js";

export function makeQueries(raw: Surreal): OlikDb {
  return {
    async listGlyphs(_opts?: ListOpts): Promise<ListPage<GlyphSummary>> {
      const rows = await raw.query<GlyphSummary[][]>(
        "SELECT char, stroke_count, radical, iou_mean FROM glyph ORDER BY char;",
      );
      return { items: rows[0] ?? [] };
    },
    async getGlyph(char: string): Promise<GlyphRecord | null> {
      const rows = await raw.query<GlyphRecord[][]>(
        "SELECT * FROM glyph WHERE char = $c;",
        { c: char },
      );
      return rows[0]?.[0] ?? null;
    },
    async listPrototypes(): Promise<PrototypeSummary[]> {
      const rows = await raw.query<PrototypeSummary[][]>(
        "SELECT id, name, usage_count FROM prototype ORDER BY id;",
      );
      return rows[0] ?? [];
    },
    async getPrototypeUsers(_id: string): Promise<GlyphSummary[]> {
      return []; // Task 8 fills this
    },
    async listVariants(_char: string): Promise<StyleVariant[]> {
      return []; // Task 9 fills this
    },
    async subscribeVariants(_char, _cb) {
      return async () => {}; // Task 9 fills this
    },
    async close(): Promise<void> {
      await raw.close();
    },
  };
}
```

- [ ] **Step 6: `src/index.ts`**

```ts
// project/ts/packages/glyph-db/src/index.ts
export { createDb, DEFAULT_DB_CONFIG } from "./client.js";
export type { DbConfig, OlikDb } from "./client.js";
export type {
  GlyphSummary, PrototypeSummary, StyleVariant,
  ListFilter, ListOpts, ListPage, Unsubscribe,
  GlyphRecord, Prototype,
} from "./types.js";
```

- [ ] **Step 7: `test/helpers.ts` — ephemeral memory server**

```ts
// project/ts/packages/glyph-db/test/helpers.ts
import { type ChildProcess, spawn } from "node:child_process";
import { createServer } from "node:net";

export async function pickPort(): Promise<number> {
  return await new Promise<number>((res, rej) => {
    const srv = createServer();
    srv.unref();
    srv.on("error", rej);
    srv.listen(0, "127.0.0.1", () => {
      const port = (srv.address() as { port: number }).port;
      srv.close(() => res(port));
    });
  });
}

export interface EphemeralSurreal {
  url:  string;
  stop: () => Promise<void>;
}

export async function startSurreal(): Promise<EphemeralSurreal> {
  const port = await pickPort();
  const proc: ChildProcess = spawn(
    "surreal",
    [
      "start",
      "--user", "root", "--pass", "root",
      "--bind", `127.0.0.1:${port}`,
      "memory",
    ],
    { stdio: "ignore" },
  );

  const url = `ws://127.0.0.1:${port}/rpc`;
  // Wait until HTTP health responds
  const httpUrl = `http://127.0.0.1:${port}/health`;
  const deadline = Date.now() + 10000;
  while (Date.now() < deadline) {
    try {
      const resp = await fetch(httpUrl);
      if (resp.ok) break;
    } catch { /* not ready */ }
    await new Promise((r) => setTimeout(r, 100));
  }

  return {
    url,
    stop: async () => {
      proc.kill("SIGTERM");
      await new Promise<void>((r) => proc.on("close", () => r()));
    },
  };
}
```

- [ ] **Step 8: `test/contract.test.ts` — sync-then-query roundtrip**

```ts
// project/ts/packages/glyph-db/test/contract.test.ts
import { afterAll, beforeAll, describe, expect, test } from "vitest";
import { Surreal } from "surrealdb";

import { createDb } from "../src/index.js";
import { startSurreal, type EphemeralSurreal } from "./helpers.js";

let srv: EphemeralSurreal;
let seedUrl: string;

// Applies the schema + inserts one glyph so the typed client has something to query.
async function seed(url: string): Promise<void> {
  const s = new Surreal();
  await s.connect(url);
  await s.signin({ username: "root", password: "root" });
  await s.use({ namespace: "hanfont", database: "olik" });
  await s.query(
    "DEFINE TABLE glyph SCHEMALESS; "
    + "DEFINE INDEX glyph_char_uniq ON glyph FIELDS char UNIQUE;",
  );
  await s.query(
    "UPDATE type::thing('glyph', '明') MERGE {char:'明', stroke_count:8, radical:'日', iou_mean:1.0};",
  );
  await s.close();
}

beforeAll(async () => {
  srv = await startSurreal();
  seedUrl = srv.url;
  await seed(seedUrl);
});

afterAll(async () => {
  await srv.stop();
});

describe("@olik/glyph-db contract", () => {
  test("listGlyphs returns the seeded glyph", async () => {
    const db = await createDb({ url: seedUrl });
    try {
      const page = await db.listGlyphs();
      expect(page.items).toEqual([{
        char: "明", stroke_count: 8, radical: "日", iou_mean: 1.0,
      }]);
    } finally {
      await db.close();
    }
  });

  test("getGlyph returns the seeded glyph record", async () => {
    const db = await createDb({ url: seedUrl });
    try {
      const rec = await db.getGlyph("明");
      expect(rec?.char).toBe("明");
    } finally {
      await db.close();
    }
  });

  test("getGlyph returns null for unknown char", async () => {
    const db = await createDb({ url: seedUrl });
    try {
      const rec = await db.getGlyph("NOPE");
      expect(rec).toBeNull();
    } finally {
      await db.close();
    }
  });
});
```

- [ ] **Step 9: Install deps + run**

```bash
cd project/ts && pnpm install --frozen-lockfile=false 2>&1 | tail -5
cd packages/glyph-db && pnpm typecheck
cd ../.. && pnpm --filter "@olik/glyph-db" test 2>&1 | tail -20
```

Expected: typecheck passes, 3 tests pass (contract suite).

- [ ] **Step 10: Commit**

```bash
git add project/ts/packages/glyph-db project/ts/pnpm-lock.yaml
git commit -m "feat(glyph-db): TS client package scaffold + contract test"
```

---

## Task 8: Fill `getPrototypeUsers` + filter/sort/paginate on `listGlyphs`

**Files:**
- Modify: `project/ts/packages/glyph-db/src/queries.ts`
- Create: `project/ts/packages/glyph-db/test/queries.test.ts`

- [ ] **Step 1: Write failing test**

```ts
// project/ts/packages/glyph-db/test/queries.test.ts
import { afterAll, beforeAll, describe, expect, test } from "vitest";
import { Surreal } from "surrealdb";

import { createDb } from "../src/index.js";
import { startSurreal, type EphemeralSurreal } from "./helpers.js";

let srv: EphemeralSurreal;

async function seedMulti(url: string): Promise<void> {
  const s = new Surreal();
  await s.connect(url);
  await s.signin({ username: "root", password: "root" });
  await s.use({ namespace: "hanfont", database: "olik" });
  await s.query(
    "DEFINE TABLE glyph SCHEMALESS;"
    + "DEFINE INDEX glyph_char_uniq ON glyph FIELDS char UNIQUE;"
    + "DEFINE INDEX glyph_stroke_ct ON glyph FIELDS stroke_count;"
    + "DEFINE INDEX glyph_radical ON glyph FIELDS radical;"
    + "DEFINE TABLE prototype SCHEMALESS;"
    + "DEFINE INDEX proto_id_uniq ON prototype FIELDS id UNIQUE;"
    + "DEFINE TABLE uses SCHEMALESS;",
  );
  for (const [char, ct, rad] of [
    ["明", 8,  "日"],
    ["清", 11, "氵"],
    ["森", 12, "木"],
  ] as const) {
    await s.query(
      "UPDATE type::thing('glyph', $c) MERGE {char:$c, stroke_count:$n, radical:$r, iou_mean:1.0};",
      { c: char, n: ct, r: rad },
    );
  }
  await s.query(
    "UPDATE type::thing('prototype', 'proto:moon') MERGE {id:'proto:moon', name:'moon'};",
  );
  await s.query(
    "RELATE type::thing('glyph','明')->uses->type::thing('prototype','proto:moon') CONTENT {instance_id:'inst1'};",
  );
  await s.close();
}

beforeAll(async () => {
  srv = await startSurreal();
  await seedMulti(srv.url);
});

afterAll(async () => { await srv.stop(); });

describe("@olik/glyph-db queries", () => {
  test("listGlyphs filter by radical", async () => {
    const db = await createDb({ url: srv.url });
    try {
      const page = await db.listGlyphs({ filter: { radical: "日" } });
      expect(page.items.map((g) => g.char)).toEqual(["明"]);
    } finally { await db.close(); }
  });

  test("listGlyphs filter by stroke count range", async () => {
    const db = await createDb({ url: srv.url });
    try {
      const page = await db.listGlyphs({ filter: { strokeCountRange: [10, 12] } });
      expect(page.items.map((g) => g.char).sort()).toEqual(["森", "清"].sort());
    } finally { await db.close(); }
  });

  test("listGlyphs sort + paginate", async () => {
    const db = await createDb({ url: srv.url });
    try {
      const first = await db.listGlyphs({ sort: "stroke_count", pageSize: 2 });
      expect(first.items.map((g) => g.char)).toEqual(["明", "清"]);
      expect(first.nextCursor).toBeDefined();
      const second = await db.listGlyphs({
        sort: "stroke_count", pageSize: 2, cursor: first.nextCursor,
      });
      expect(second.items.map((g) => g.char)).toEqual(["森"]);
      expect(second.nextCursor).toBeUndefined();
    } finally { await db.close(); }
  });

  test("getPrototypeUsers finds chars using a prototype", async () => {
    const db = await createDb({ url: srv.url });
    try {
      const users = await db.getPrototypeUsers("proto:moon");
      expect(users.map((g) => g.char)).toEqual(["明"]);
    } finally { await db.close(); }
  });
});
```

- [ ] **Step 2: Confirm fails (pagination + filter not yet implemented)**

```bash
pnpm --filter "@olik/glyph-db" test 2>&1 | tail -20
```

Expected: the 4 new tests fail; contract tests still pass.

- [ ] **Step 3: Fill in filter/sort/paginate + getPrototypeUsers**

Replace the body of `src/queries.ts` with:

```ts
// project/ts/packages/glyph-db/src/queries.ts
import type { Surreal } from "surrealdb";

import type {
  GlyphSummary, ListOpts, ListPage, PrototypeSummary, StyleVariant,
} from "./types.js";
import type { GlyphRecord } from "@olik/glyph-schema";
import type { OlikDb } from "./client.js";

function buildListQuery(opts: ListOpts | undefined) {
  const clauses: string[] = [];
  const bind: Record<string, unknown> = {};
  const f = opts?.filter ?? {};
  if (f.radical !== undefined) { clauses.push("radical = $rad"); bind.rad = f.radical; }
  if (f.strokeCountRange !== undefined) {
    clauses.push("stroke_count >= $lo AND stroke_count <= $hi");
    bind.lo = f.strokeCountRange[0]; bind.hi = f.strokeCountRange[1];
  }
  if (f.iouBelow !== undefined) { clauses.push("iou_mean < $iou"); bind.iou = f.iouBelow; }
  const where = clauses.length ? ` WHERE ${clauses.join(" AND ")}` : "";

  const sortField = opts?.sort ?? "char";
  const limit = opts?.pageSize ?? 50;
  // Keyset pagination: cursor is the last seen sort-field value.
  let cursorClause = "";
  if (opts?.cursor !== undefined) {
    cursorClause = clauses.length
      ? ` AND ${sortField} > $cursor`
      : ` WHERE ${sortField} > $cursor`;
    bind.cursor = opts.cursor;
  }
  const sql =
    "SELECT char, stroke_count, radical, iou_mean FROM glyph"
    + where + cursorClause
    + ` ORDER BY ${sortField} LIMIT ${limit + 1};`;
  return { sql, bind, limit, sortField };
}

export function makeQueries(raw: Surreal): OlikDb {
  return {
    async listGlyphs(opts?: ListOpts): Promise<ListPage<GlyphSummary>> {
      const { sql, bind, limit, sortField } = buildListQuery(opts);
      const rows = (await raw.query<GlyphSummary[][]>(sql, bind))[0] ?? [];
      const hasMore = rows.length > limit;
      const items = hasMore ? rows.slice(0, limit) : rows;
      const cursor = hasMore
        ? String((items[items.length - 1] as Record<string, unknown>)[sortField])
        : undefined;
      return { items, nextCursor: cursor };
    },

    async getGlyph(char: string): Promise<GlyphRecord | null> {
      const rows = await raw.query<GlyphRecord[][]>(
        "SELECT * FROM glyph WHERE char = $c;", { c: char },
      );
      return rows[0]?.[0] ?? null;
    },

    async listPrototypes(): Promise<PrototypeSummary[]> {
      const rows = await raw.query<PrototypeSummary[][]>(
        "SELECT id, name, usage_count FROM prototype ORDER BY id;",
      );
      return rows[0] ?? [];
    },

    async getPrototypeUsers(id: string): Promise<GlyphSummary[]> {
      const rows = await raw.query<GlyphSummary[][]>(
        "SELECT char, stroke_count, radical, iou_mean "
        + "FROM (SELECT <-uses<-glyph AS g FROM type::thing('prototype', $id))[0].g "
        + "ORDER BY char;",
        { id },
      );
      return rows[0] ?? [];
    },

    async listVariants(_char: string): Promise<StyleVariant[]> {
      return []; // Task 9 fills this
    },

    async subscribeVariants(_char, _cb) {
      return async () => {}; // Task 9 fills this
    },

    async close(): Promise<void> {
      await raw.close();
    },
  };
}
```

- [ ] **Step 4: Rerun tests**

```bash
pnpm --filter "@olik/glyph-db" test 2>&1 | tail -20
```

Expected: contract (3) + queries (4) = 7 tests pass.

- [ ] **Step 5: Commit**

```bash
git add project/ts/packages/glyph-db/src/queries.ts project/ts/packages/glyph-db/test/queries.test.ts
git commit -m "feat(glyph-db): list filters + keyset pagination + getPrototypeUsers"
```

---

## Task 9: LIVE query — `listVariants` + `subscribeVariants`

**Files:**
- Modify: `project/ts/packages/glyph-db/src/queries.ts`
- Create: `project/ts/packages/glyph-db/test/live.test.ts`

- [ ] **Step 1: Write failing test**

```ts
// project/ts/packages/glyph-db/test/live.test.ts
import { afterAll, beforeAll, describe, expect, test } from "vitest";
import { Surreal } from "surrealdb";

import { createDb } from "../src/index.js";
import { startSurreal, type EphemeralSurreal } from "./helpers.js";

let srv: EphemeralSurreal;

async function seed(url: string): Promise<void> {
  const s = new Surreal();
  await s.connect(url);
  await s.signin({ username: "root", password: "root" });
  await s.use({ namespace: "hanfont", database: "olik" });
  await s.query(
    "DEFINE TABLE glyph SCHEMALESS;"
    + "DEFINE TABLE style_variant SCHEMALESS;"
    + "DEFINE INDEX sv_char_style ON style_variant FIELDS char, style_name UNIQUE;",
  );
  await s.query(
    "UPDATE type::thing('glyph', '明') MERGE {char:'明', stroke_count:8};",
  );
  await s.close();
}

beforeAll(async () => {
  srv = await startSurreal();
  await seed(srv.url);
});

afterAll(async () => { await srv.stop(); });

describe("live variants", () => {
  test("listVariants empty initially", async () => {
    const db = await createDb({ url: srv.url });
    try {
      const v = await db.listVariants("明");
      expect(v).toEqual([]);
    } finally { await db.close(); }
  });

  test("subscribeVariants receives new rows", async () => {
    const db = await createDb({ url: srv.url });
    const received: unknown[] = [];
    const unsub = await db.subscribeVariants("明", (v) => received.push(v));
    // Insert a variant row via a separate client so the LIVE query fires.
    const writer = new Surreal();
    await writer.connect(srv.url);
    await writer.signin({ username: "root", password: "root" });
    await writer.use({ namespace: "hanfont", database: "olik" });
    await writer.query(
      "CREATE style_variant CONTENT "
      + "{char:'明', style_name:'brush', image_ref:'/tmp/x.png', status:'done'};",
    );
    await writer.close();
    // Poll up to 5s for delivery
    const deadline = Date.now() + 5000;
    while (received.length === 0 && Date.now() < deadline) {
      await new Promise((r) => setTimeout(r, 100));
    }
    await unsub();
    await db.close();
    expect(received.length).toBeGreaterThan(0);
  });
});
```

- [ ] **Step 2: Verify fails**

```bash
pnpm --filter "@olik/glyph-db" test 2>&1 | tail -20
```

Expected: the 2 live tests fail (subscribeVariants still returns noop unsub).

- [ ] **Step 3: Implement LIVE subscription in `queries.ts`**

Replace the `listVariants` and `subscribeVariants` methods with:

```ts
    async listVariants(char: string): Promise<StyleVariant[]> {
      const rows = await raw.query<StyleVariant[][]>(
        "SELECT char, style_name, image_ref, workflow_id, status, generated_at "
        + "FROM style_variant WHERE char = $c ORDER BY generated_at;",
        { c: char },
      );
      return rows[0] ?? [];
    },

    async subscribeVariants(char, cb) {
      const [liveId] = await raw.query<[string]>(
        "LIVE SELECT * FROM style_variant WHERE char = $c;", { c: char },
      );
      const handler = (action: string, result: unknown) => {
        if (action === "CREATE" || action === "UPDATE") {
          cb(result as StyleVariant);
        }
      };
      // surrealdb v1.x: subscribeLive returns an unsubscribe handle
      await raw.subscribeLive(liveId as unknown as string, handler);
      return async () => {
        try {
          await raw.kill(liveId as unknown as string);
        } catch {
          // connection may already be closed
        }
      };
    },
```

- [ ] **Step 4: Rerun**

```bash
pnpm --filter "@olik/glyph-db" test 2>&1 | tail -20
```

Expected: all 9 tests pass (contract 3 + queries 4 + live 2).

- [ ] **Step 5: Commit**

```bash
git add project/ts/packages/glyph-db/src/queries.ts project/ts/packages/glyph-db/test/live.test.ts
git commit -m "feat(glyph-db): LIVE subscription for style_variant rows"
```

---

## Task 10: Taskfile lanes + final verification + tag

**Files:**
- Modify: `Taskfile.yml`
- Modify: `vault/plans/2026-04-21-08-surrealdb-foundation.md` (status → complete, no plan body change)

- [ ] **Step 1: Add DB lanes to `Taskfile.yml`**

Append (keeping conventions consistent with existing lanes):

```yaml
  db:up:
    desc: Start the persistent SurrealDB (surrealkv://infra/surrealdb/data) if not running
    cmds:
      - |
        if lsof -ti:6480 >/dev/null 2>&1; then
          echo "already listening on 6480"
        else
          mkdir -p infra/surrealdb/data
          nohup surreal start --user root --pass root --bind 0.0.0.0:6480 \
            "surrealkv://$(pwd)/infra/surrealdb/data" \
            > /tmp/surrealdb.log 2>&1 &
          echo "started PID $!"
        fi

  db:down:
    desc: Stop whichever surreal process is on :6480
    cmds:
      - |
        pid=$(lsof -ti:6480 2>/dev/null || true)
        if [ -n "$pid" ]; then kill "$pid" && echo "stopped $pid"; else echo "nothing on 6480"; fi

  db:reset:
    desc: Wipe the persistent DB directory and re-seed
    deps: [db:down]
    cmds:
      - rm -rf infra/surrealdb/data/*
      - task: db:up
      - "{{.VENV}}/bin/olik db reset --yes"
      - task: db:seed

  db:seed:
    desc: Populate hanfont/olik with the 4 seed chars
    cmds:
      - "{{.VENV}}/bin/olik db sync 明 清 國 森"

  db:export:
    desc: Dump hanfont/olik back to JSON under infra/surrealdb/snapshots/<date>
    cmds:
      - |
        dir="infra/surrealdb/snapshots/$(date +%Y-%m-%d)"
        mkdir -p "$dir"
        "{{.VENV}}/bin/olik" db export --out "$dir"
        echo "wrote $dir"
```

If the file already defines a `vars.VENV` pointing at `project/py/.venv`, the `{{.VENV}}/bin/olik` references work out of the box. Confirm by reading the first 20 lines of the file before editing.

- [ ] **Step 2: Workspace-wide verification**

```bash
cd project/py && .venv/bin/pytest -q 2>&1 | tail -5
cd ../ts && pnpm -r typecheck 2>&1 | tail -10
cd ../ts && pnpm -r test 2>&1 | tail -20
```

Expected: Python passes (old tests + ~12 new sink tests + xfail on 國 remains); TS typecheck all green; TS tests include `@olik/glyph-db` 9 tests.

- [ ] **Step 3: End-to-end smoke**

Against the real dev instance (must be running from brainstorming — `task db:up` if not):

```bash
task db:up
task db:reset
task db:seed
task db:export
ls infra/surrealdb/snapshots/$(date +%Y-%m-%d)/
```

Expected: directory contains `prototype-library.json`, `rules.json`, `glyph-record-明.json`, `glyph-record-清.json`, `glyph-record-國.json`, `glyph-record-森.json`, `rule-trace-*.json`.

- [ ] **Step 4: Update plan status frontmatter**

Edit `vault/plans/2026-04-21-08-surrealdb-foundation.md` and change `status: draft` → `status: complete` in the frontmatter (and nothing else).

- [ ] **Step 5: Tag + commit**

```bash
git add Taskfile.yml vault/plans/2026-04-21-08-surrealdb-foundation.md
git commit -m "chore(db): Taskfile db:* lanes + plan-08 status=complete"
git tag -a plan-08-surrealdb-foundation \
  -m "Plan 08 complete — SurrealDB foundation"
```

---

## Self-review checklist (for the engineer before merging)

- [ ] All 10 tasks committed in order, each with the commit message spelled above.
- [ ] `pytest -q` green in `project/py/` including the new 12+ sink tests.
- [ ] `pnpm -r test` green across the TS workspace; `@olik/glyph-db` reports 9 passed.
- [ ] `task db:seed` populates the running persistent DB without errors.
- [ ] `task db:export` snapshot matches the existing `project/schema/examples/*.json` byte-for-byte (modulo key ordering).
- [ ] `pnpm -r build` excluding `@olik/remotion-studio` still passes (no Plan-06 regressions).
- [ ] `plan-08-surrealdb-foundation` tag is present.

## Follow-ups for later plans

- **Plan 09**: bulk extraction — auto-generated plans from cjk-decomp + MMH, 500-char ingest, prototype library growth, human-in-loop review tooling. First consumer of `olik db sync`.
- **Plan 10**: Refine / react-admin shell over `@olik/glyph-db`, virtualized list, search/filter/sort, detail drawer embedding the existing inspector xyflow views. First consumer of `subscribeVariants` (wired but empty until Plan 11).
- **Plan 11**: ComfyUI MVP — workflow submission, job runner writing `style_variant` rows, admin UI variant tab comes alive.

## Adjustments after execution

_Notes on field-name drift, SurrealDB protocol surprises, or test-harness flakiness found during implementation._

- Task 2: the installed SurrealDB build rejected `type::thing(...)`, and `UPDATE ... MERGE` did not create missing rows; `project/py/src/olik_font/sink/surrealdb.py` uses `UPSERT type::record(...) MERGE ...` instead with no behavior change.
- Task 2: the Python client returns `SELECT` payloads as row lists and record IDs as `RecordID` objects, so sink tests normalize both shapes before asserting.
