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


def upsert_rules(db: Surreal, rules: list[dict[str, Any]]) -> None:
    """Idempotent write of the rule catalog."""
    for rule in rules:
        db.query(
            "UPSERT type::record('rule', $key) MERGE $data;",
            {"key": rule["id"], "data": rule},
        )


def upsert_rule_trace(
    db: Surreal,
    glyph_char: str,
    trace: list[dict[str, Any]],
) -> None:
    """Rewrite the rule_trace log and `cites` edges for one glyph."""
    glyph_ref = _record_ref("glyph", glyph_char)

    db.query(
        "BEGIN TRANSACTION;"
        "DELETE rule_trace WHERE glyph = <record>$glyph;"
        "DELETE cites WHERE in = <record>$glyph;"
        "COMMIT TRANSACTION;",
        {"glyph": glyph_ref},
    )

    for entry in trace:
        rule_ref = _record_ref("rule", entry["rule_id"])
        db.query(
            "CREATE rule_trace SET "
            "glyph = <record>$glyph, "
            "rule = <record>$rule, "
            "fired = $fired, "
            "order = $order, "
            "alternative = $alternative;",
            {
                "glyph": glyph_ref,
                "rule": rule_ref,
                "fired": entry["fired"],
                "order": entry["order"],
                "alternative": entry.get("alternative", False),
            },
        )
        db.query(
            f"RELATE {glyph_ref}->cites->{rule_ref} CONTENT $edge;",
            {
                "edge": {
                    "order": entry["order"],
                    "alternative": entry.get("alternative", False),
                }
            },
        )
