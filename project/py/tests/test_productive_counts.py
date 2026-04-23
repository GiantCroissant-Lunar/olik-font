"""productive_count is derived from `uses` edge multiplicity."""

from __future__ import annotations

from typing import Any

from olik_font.sink.connection import DbConfig, connect
from olik_font.sink.schema import ensure_schema
from olik_font.sink.surrealdb import (
    compute_productive_counts,
    upsert_glyph,
    upsert_prototype,
)

PROTOS = [
    {"id": "proto:sun", "name": "sun", "source": "authored", "strokes": []},
    {"id": "proto:moon", "name": "moon", "source": "authored", "strokes": []},
    {"id": "proto:wood", "name": "wood", "source": "authored", "strokes": []},
]


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


def _record(proto_ref: str, char: str, *instance_ids: str) -> dict[str, Any]:
    return {
        "char": char,
        "iou_report": {"mean": 1.0},
        "layout_tree": {"id": char, "mode": "keep", "children": []},
        "component_instances": [
            {
                "id": instance_id,
                "prototype_ref": proto_ref,
                "position": "test",
                "placed_bbox": [0, 0, 1, 1],
            }
            for instance_id in instance_ids
        ],
    }


def _record_key(value: object) -> str:
    record_id = getattr(value, "id", None)
    if isinstance(record_id, str):
        return record_id
    record_id = getattr(value, "record_id", None)
    if isinstance(record_id, str):
        return record_id
    text = str(value)
    prefix = "prototype:"
    if text.startswith(prefix):
        return text[len(prefix) :].removeprefix("⟨").removesuffix("⟩")
    return text


def test_compute_productive_counts_returns_expected_multiplicity(
    surreal_ephemeral: DbConfig,
) -> None:
    db = connect(surreal_ephemeral)
    ensure_schema(db)
    for proto in PROTOS:
        upsert_prototype(db, proto)

    upsert_glyph(
        db,
        {
            **_record("proto:sun", "明", "sun-1", "sun-2"),
            "component_instances": [
                *_record("proto:sun", "明", "sun-1", "sun-2")["component_instances"],
                *_record("proto:moon", "明", "moon-1")["component_instances"],
            ],
        },
    )
    upsert_glyph(
        db,
        {
            **_record("proto:sun", "杲", "sun-3"),
            "component_instances": [
                *_record("proto:sun", "杲", "sun-3")["component_instances"],
                *_record("proto:wood", "杲", "wood-1")["component_instances"],
            ],
        },
    )

    counts = compute_productive_counts(db)
    assert counts == {"proto:sun": 3, "proto:moon": 1, "proto:wood": 1}

    rows = _rows(db.query("SELECT id, productive_count FROM prototype ORDER BY id;"))
    normalized = {_record_key(row["id"]): row["productive_count"] for row in rows}
    assert normalized == {"proto:moon": 1, "proto:sun": 3, "proto:wood": 1}
