"""upsert_rules stores rules + rule_trace + cites edges."""

from __future__ import annotations

from olik_font.sink.connection import DbConfig, connect
from olik_font.sink.schema import ensure_schema
from olik_font.sink.surrealdb import (
    upsert_glyph,
    upsert_rule_trace,
    upsert_rules,
)

BASIC_GLYPH = {
    "char": "明",
    "stroke_count": 8,
    "radical": "日",
    "iou_mean": 1.0,
    "stroke_instances": [],
    "layout_tree": {},
    "render_layers": [],
    "iou_report": {},
    "component_instances": [],
}

RULES = [
    {
        "id": "rule:left_right_day",
        "pattern": "日+X",
        "bucket": "decomp",
        "resolution": "left_right",
    },
    {
        "id": "rule:left_right_moon",
        "pattern": "X+月",
        "bucket": "decomp",
        "resolution": "left_right",
    },
]

TRACE = [
    {"rule_id": "rule:left_right_day", "fired": True, "order": 0, "alternative": False},
    {"rule_id": "rule:left_right_moon", "fired": False, "order": 1, "alternative": True},
]


def _rows(payload: object) -> list[dict[str, object]]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        return payload["result"]
    raise TypeError(f"unexpected query payload: {type(payload)!r}")


def test_upsert_rules_and_trace(surreal_ephemeral: DbConfig) -> None:
    db = connect(surreal_ephemeral)
    ensure_schema(db)

    upsert_rules(db, RULES)
    upsert_glyph(db, BASIC_GLYPH)
    upsert_rule_trace(db, "明", TRACE)

    rule_rows = _rows(db.query("SELECT id, pattern, bucket FROM rule ORDER BY id;"))
    assert len(rule_rows) == 2

    trace_rows = _rows(
        db.query(
            "SELECT fired, order FROM rule_trace "
            "WHERE glyph = type::record('glyph', '明') ORDER BY order;"
        )
    )
    assert trace_rows == [
        {"fired": True, "order": 0},
        {"fired": False, "order": 1},
    ]

    cites = _rows(
        db.query(
            "SELECT alternative, order FROM cites WHERE in = type::record('glyph', '明') "
            "ORDER BY order;"
        )
    )
    assert cites == [
        {"alternative": False, "order": 0},
        {"alternative": True, "order": 1},
    ]
