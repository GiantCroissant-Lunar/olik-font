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
    "stroke_instances": [{"id": "s0"}, {"id": "s1"}],
    "layout_tree": {"id": "明", "mode": "left_right", "children": []},
    "render_layers": [],
    "iou_report": {"mean": 1.0, "per_group": {}},
    "component_instances": [
        {
            "id": "inst1",
            "prototype_ref": "proto:moon",
            "position": "right",
            "placed_bbox": [0, 0, 1, 1],
        }
    ],
}


def _rows(payload: object) -> list[dict[str, object]]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        return payload["result"]
    raise TypeError(f"unexpected query payload: {type(payload)!r}")


def test_upsert_glyph_row_and_edges(surreal_ephemeral: DbConfig) -> None:
    db = connect(surreal_ephemeral)
    ensure_schema(db)
    upsert_prototype(db, SAMPLE_PROTO)
    upsert_glyph(db, SAMPLE_RECORD)

    rows = _rows(db.query("SELECT char, stroke_count, radical, iou_mean FROM glyph;"))
    assert rows == [{"char": "明", "stroke_count": 8, "radical": "日", "iou_mean": 1.0}]

    edges = _rows(
        db.query("SELECT instance_id, position FROM uses WHERE in = type::record('glyph', '明');")
    )
    assert edges == [{"instance_id": "inst1", "position": "right"}]


def test_upsert_glyph_edges_rebuilt_on_resync(surreal_ephemeral: DbConfig) -> None:
    db = connect(surreal_ephemeral)
    ensure_schema(db)
    upsert_prototype(db, SAMPLE_PROTO)
    upsert_glyph(db, SAMPLE_RECORD)

    upsert_glyph(db, {**SAMPLE_RECORD, "component_instances": []})
    edges = _rows(db.query("SELECT * FROM uses WHERE in = type::record('glyph', '明');"))
    assert edges == []
