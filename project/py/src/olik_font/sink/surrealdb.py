"""Write-side helpers - upserts + RELATE wiring."""

from __future__ import annotations

import re
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


def _query_rows(payload: object) -> list[dict[str, Any]]:
    """Normalize surrealdb-python 1.x/2.x query payloads."""
    if isinstance(payload, list):
        if payload and isinstance(payload[0], dict) and "result" in payload[0]:
            return payload[0]["result"]
        return payload
    if isinstance(payload, dict):
        result = payload.get("result", [])
        if isinstance(result, list):
            return result
    raise TypeError(f"unexpected query payload: {type(payload)!r}")


def _record_id_component(value: object) -> str:
    """Extract the raw record-id component from a Surreal record reference."""
    for attr in ("id", "record_id"):
        raw = getattr(value, attr, None)
        if isinstance(raw, str):
            return raw
    text = str(value)
    match = re.search(r"record_id='([^']+)'", text)
    if match is not None:
        return match.group(1)
    if ":" in text:
        return text.split(":", 1)[1].removeprefix("⟨").removesuffix("⟩")
    return text


def _upsert_relation_edge(
    db: Surreal,
    *,
    table: str,
    in_table: str,
    in_id: str,
    out_table: str,
    out_id: str,
    content: dict[str, Any] | None = None,
    unique_on_in_only: bool = False,
) -> None:
    """Create or update a relation row without duplicating edges."""
    if unique_on_in_only:
        query = (
            f"SELECT id, out FROM {table} WHERE in = type::record('{in_table}', $in_id) LIMIT 1;"
        )
        rows = _query_rows(db.query(query, {"in_id": in_id}))
        if rows:
            row = rows[0]
            db.query("DELETE <record>$edge_id;", {"edge_id": str(row["id"])})
    else:
        query = (
            f"SELECT id FROM {table} "
            f"WHERE in = type::record('{in_table}', $in_id) "
            f"AND out = type::record('{out_table}', $out_id) LIMIT 1;"
        )
        rows = _query_rows(db.query(query, {"in_id": in_id, "out_id": out_id}))
        if rows:
            if content:
                db.query(
                    "UPDATE <record>$edge_id MERGE $content;",
                    {"edge_id": str(rows[0]["id"]), "content": content},
                )
            return

    in_ref = _record_ref(in_table, in_id)
    out_ref = _record_ref(out_table, out_id)
    params: dict[str, Any] = {}
    content_sql = ""
    if content:
        params["content"] = content
        content_sql = " CONTENT $content"
    db.query(f"RELATE {in_ref}->{table}->{out_ref}{content_sql};", params)


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
    radical: str | None = None,
    etymology: str | None = None,
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
    if radical is not None:
        body["radical"] = radical
    if etymology is not None:
        body["etymology"] = etymology
    db.query(
        "UPSERT type::record('glyph', $char) MERGE $data;",
        {"char": char, "data": body},
    )


def upsert_decomposes_into(
    db: Surreal,
    parent_id: str,
    child_id: str,
    ordinal: int,
    source: str,
) -> None:
    """Create-or-update a prototype->prototype decomposition edge."""
    _upsert_relation_edge(
        db,
        table="decomposes_into",
        in_table="prototype",
        in_id=parent_id,
        out_table="prototype",
        out_id=child_id,
        content={"ordinal": ordinal, "source": source},
    )


def upsert_appears_in(
    db: Surreal,
    proto_id: str,
    glyph_char: str,
    instance_count: int,
) -> None:
    """Create-or-update a prototype->glyph inverse-usage edge."""
    _upsert_relation_edge(
        db,
        table="appears_in",
        in_table="prototype",
        in_id=proto_id,
        out_table="glyph",
        out_id=glyph_char,
        content={"instance_count": instance_count},
    )


def upsert_has_kangxi(
    db: Surreal,
    glyph_char: str,
    kangxi_proto_id: str,
) -> None:
    """Ensure one glyph->prototype Kangxi relation per glyph."""
    _upsert_relation_edge(
        db,
        table="has_kangxi",
        in_table="glyph",
        in_id=glyph_char,
        out_table="prototype",
        out_id=kangxi_proto_id,
        unique_on_in_only=True,
    )


def compute_productive_counts(db: Surreal) -> dict[str, int]:
    """Recompute `prototype.productive_count` from `uses` edge counts."""
    rows = _query_rows(db.query("SELECT out AS proto_ref, count() AS n FROM uses GROUP BY out;"))
    counts = {_record_id_component(row["proto_ref"]): int(row["n"]) for row in rows}

    db.query("UPDATE prototype SET productive_count = 0;")
    for proto_id, count in counts.items():
        db.query(
            "UPDATE type::record('prototype', $proto_id) SET productive_count = $count;",
            {"proto_id": proto_id, "count": count},
        )
    return counts


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
    existing = _query_rows(
        db.query(
            "SELECT id FROM variant_of "
            "WHERE in = type::record('prototype', $v) "
            "  AND out = type::record('prototype', $c) LIMIT 1;",
            {"v": variant_id, "c": canonical_id},
        )
    )
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
