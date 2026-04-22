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
        "UPSERT type::record('glyph', $char) MERGE $data;",
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
    payload = db.query(
        "SELECT id FROM variant_of "
        "WHERE in = type::record('prototype', $v) "
        "  AND out = type::record('prototype', $c) LIMIT 1;",
        {"v": variant_id, "c": canonical_id},
    )
    # surrealdb-python 1.x returns [{"result": [...]}]; 2.x returns [...]
    # directly. Normalize both shapes.
    if isinstance(payload, list):
        if payload and isinstance(payload[0], dict) and "result" in payload[0]:
            existing = payload[0]["result"]
        else:
            existing = payload
    elif isinstance(payload, dict):
        existing = payload.get("result", [])
    else:
        existing = []
    if existing:
        return
    # RELATE does not accept type::record() in newer SurrealDB versions;
    # use angle-bracket identifier escape to tolerate colons and
    # non-ASCII characters (variant ids include both, e.g.
    # prototype:⟨proto:u6728_in_林⟩).
    db.query(
        f"RELATE prototype:⟨{variant_id}⟩->variant_of->prototype:⟨{canonical_id}⟩ "
        "CONTENT { reason: $r };",
        {"r": reason},
    )
