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


def _rows(payload: object) -> list[dict[str, object]]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        return payload["result"]
    raise TypeError(f"unexpected query payload: {type(payload)!r}")


def _record_id(value: object) -> str:
    if isinstance(value, str):
        return value
    record_id = getattr(value, "id", None)
    if isinstance(record_id, str):
        return record_id
    raise TypeError(f"unexpected record id payload: {type(value)!r}")


def test_upsert_prototype_single(surreal_ephemeral: DbConfig) -> None:
    db = connect(surreal_ephemeral)
    ensure_schema(db)
    upsert_prototype(db, SAMPLE)
    rows = _rows(db.query("SELECT id, name FROM prototype;"))
    assert len(rows) == 1
    assert _record_id(rows[0]["id"]) == "proto:moon"
    assert rows[0]["name"] == "moon"


def test_upsert_prototype_idempotent(surreal_ephemeral: DbConfig) -> None:
    db = connect(surreal_ephemeral)
    ensure_schema(db)
    upsert_prototype(db, SAMPLE)
    upsert_prototype(db, {**SAMPLE, "name": "moon_updated"})
    rows = _rows(db.query("SELECT id, name FROM prototype;"))
    assert len(rows) == 1
    assert rows[0]["name"] == "moon_updated"
