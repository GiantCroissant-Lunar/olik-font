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


def upsert_prototype(db: Surreal, proto: dict[str, Any]) -> None:
    """Create-or-replace a prototype row keyed on `proto["id"]`."""
    db.query(
        "UPSERT type::record('prototype', $key) MERGE $data;",
        {"key": _slug_id(proto["id"]), "data": proto},
    )
