"""Graph-schema migrations and relation helpers for Plan 14 Task 4."""

from __future__ import annotations

from typing import Any

from olik_font.sink.connection import DbConfig, connect
from olik_font.sink.schema import ensure_schema
from olik_font.sink.surrealdb import (
    upsert_appears_in,
    upsert_decomposes_into,
    upsert_glyph_stub,
    upsert_has_kangxi,
    upsert_prototype,
)

PARENT_PROTO = {
    "id": "proto:word",
    "name": "word",
    "source": "authored",
    "strokes": [],
}

CHILD_PROTO = {
    "id": "proto:speech",
    "name": "speech",
    "source": "authored",
    "strokes": [],
}

RADICAL_PROTO = {
    "id": "proto:kangxi_sun",
    "name": "sun radical",
    "source": "mmh",
    "strokes": [],
}


def _rows(payload: object) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        if payload and isinstance(payload[0], dict) and "result" in payload[0]:
            return payload[0]["result"]
        return payload
    if isinstance(payload, dict):
        result = payload.get("result", [])
        if isinstance(result, list):
            return result
    raise TypeError(f"unexpected query payload: {type(payload)!r}")


def _table_names(info: object) -> set[str]:
    if isinstance(info, dict) and "tables" in info:
        tables = info.get("tables")
        if isinstance(tables, dict):
            return set(tables.keys())
    rows = _rows(info)
    if not rows:
        raise AssertionError("INFO FOR DB returned no rows")
    tables = rows[0].get("tables")
    if not isinstance(tables, dict):
        raise TypeError(f"unexpected INFO FOR DB payload: {rows[0]!r}")
    return set(tables.keys())


def _record_ref(value: object) -> tuple[str, str]:
    table_name = getattr(value, "table_name", None)
    if isinstance(table_name, str):
        rendered = str(value)
        prefix = f"{table_name}:"
        if rendered.startswith(prefix):
            return table_name, rendered.removeprefix(prefix).strip("⟨⟩")
    raise TypeError(f"unexpected record reference payload: {value!r}")


def test_ensure_schema_adds_plan14_graph_tables(surreal_ephemeral: DbConfig) -> None:
    db = connect(surreal_ephemeral)
    ensure_schema(db)
    ensure_schema(db)

    tables = _table_names(db.query("INFO FOR DB;"))
    assert {"decomposes_into", "appears_in", "has_kangxi"} <= tables


def test_upsert_decomposes_into_round_trips_and_updates(surreal_ephemeral: DbConfig) -> None:
    db = connect(surreal_ephemeral)
    ensure_schema(db)
    upsert_prototype(db, PARENT_PROTO)
    upsert_prototype(db, CHILD_PROTO)

    upsert_decomposes_into(db, PARENT_PROTO["id"], CHILD_PROTO["id"], ordinal=0, source="authored")
    upsert_decomposes_into(db, PARENT_PROTO["id"], CHILD_PROTO["id"], ordinal=1, source="mmh")

    rows = _rows(
        db.query(
            "SELECT ordinal, source FROM decomposes_into "
            "WHERE in = type::record('prototype', $parent) "
            "AND out = type::record('prototype', $child);",
            {"parent": PARENT_PROTO["id"], "child": CHILD_PROTO["id"]},
        )
    )
    assert rows == [{"ordinal": 1, "source": "mmh"}]


def test_upsert_appears_in_round_trips_and_updates(surreal_ephemeral: DbConfig) -> None:
    db = connect(surreal_ephemeral)
    ensure_schema(db)
    upsert_prototype(db, CHILD_PROTO)
    upsert_glyph_stub(db, "語", "verified")

    upsert_appears_in(db, CHILD_PROTO["id"], "語", instance_count=1)
    upsert_appears_in(db, CHILD_PROTO["id"], "語", instance_count=3)

    rows = _rows(
        db.query(
            "SELECT instance_count FROM appears_in "
            "WHERE in = type::record('prototype', $proto) "
            "AND out = type::record('glyph', $char);",
            {"proto": CHILD_PROTO["id"], "char": "語"},
        )
    )
    assert rows == [{"instance_count": 3}]


def test_upsert_has_kangxi_round_trips(surreal_ephemeral: DbConfig) -> None:
    db = connect(surreal_ephemeral)
    ensure_schema(db)
    upsert_glyph_stub(db, "明", "verified")
    upsert_prototype(db, RADICAL_PROTO)

    upsert_has_kangxi(db, "明", RADICAL_PROTO["id"])
    upsert_has_kangxi(db, "明", RADICAL_PROTO["id"])

    rows = _rows(
        db.query(
            "SELECT in, out FROM has_kangxi WHERE in = type::record('glyph', $char);",
            {"char": "明"},
        )
    )
    assert len(rows) == 1
    assert _record_ref(rows[0]["in"]) == ("glyph", "明")
    assert _record_ref(rows[0]["out"]) == ("prototype", RADICAL_PROTO["id"])
