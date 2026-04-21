"""ensure_schema is idempotent and creates the expected tables."""

from __future__ import annotations

from olik_font.sink.connection import DbConfig, connect
from olik_font.sink.schema import ensure_schema

EXPECTED_TABLES = {
    "glyph",
    "prototype",
    "rule",
    "rule_trace",
    "extraction_run",
    "style_variant",
    "comfyui_job",
    "uses",
    "cites",
}


def _table_names(info: object) -> set[str]:
    if isinstance(info, list):
        return set(info[0]["result"]["tables"].keys())
    if isinstance(info, dict):
        return set(info["tables"].keys())
    raise TypeError(f"unexpected INFO FOR DB payload: {type(info)!r}")


def test_ensure_schema_creates_tables(surreal_ephemeral: DbConfig) -> None:
    db = connect(surreal_ephemeral)
    ensure_schema(db)
    info = db.query("INFO FOR DB;")
    tables = _table_names(info)
    missing = EXPECTED_TABLES - tables
    assert missing == set(), f"missing tables: {missing}"


def test_ensure_schema_idempotent(surreal_ephemeral: DbConfig) -> None:
    db = connect(surreal_ephemeral)
    ensure_schema(db)
    ensure_schema(db)
    info = db.query("INFO FOR DB;")
    tables = _table_names(info)
    assert tables >= EXPECTED_TABLES
