"""Write-side helpers - upserts + RELATE wiring."""

from __future__ import annotations

from typing import Any

from surrealdb import Surreal


def _slug_id(raw: str) -> str:
    """Quote a Surreal record-ID component so unicode chars and colons are safe.

    Surreal's `type::thing(table, id)` takes the id as a value; passing the raw
    string through a parameter handles escaping for us.
    """
    return raw


def _record_ref(table: str, raw: str) -> str:
    """Build a quoted record reference accepted by RELATE on this Surreal build."""
    escaped = raw.replace("`", "\\`")
    return f"{table}:`{escaped}`"


def upsert_prototype(db: Surreal, proto: dict[str, Any]) -> None:
    """Create-or-replace a prototype row keyed on `proto["id"]`."""
    db.query(
        "UPSERT type::record('prototype', $key) MERGE $data;",
        {"key": _slug_id(proto["id"]), "data": proto},
    )


def upsert_glyph(db: Surreal, record: dict[str, Any]) -> None:
    """Create-or-replace a glyph and rebuild its `uses` edges."""
    char = record["char"]
    body = {key: value for key, value in record.items() if key != "component_instances"}
    glyph_ref = _record_ref("glyph", char)

    db.query(
        "BEGIN TRANSACTION;"
        "UPSERT type::record('glyph', $char) MERGE $data;"
        "DELETE uses WHERE in = <record>$glyph;"
        "COMMIT TRANSACTION;",
        {"char": char, "data": body, "glyph": glyph_ref},
    )

    for inst in record.get("component_instances", []):
        proto_ref = _record_ref("prototype", inst["prototype_ref"])
        db.query(
            f"RELATE {glyph_ref}->uses->{proto_ref} CONTENT $edge;",
            {
                "edge": {
                    "instance_id": inst["id"],
                    "position": inst.get("position"),
                    "placed_bbox": inst.get("placed_bbox"),
                },
            },
        )
