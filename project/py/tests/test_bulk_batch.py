"""run_batch — orchestrates bucket selection + planning + upsert."""

from __future__ import annotations

import olik_font.bulk.batch as bulk_batch
from olik_font.bulk.batch import BatchReport, run_batch
from olik_font.bulk.status import Status
from olik_font.sink.connection import DbConfig, connect
from olik_font.sink.schema import ensure_schema
from olik_font.sink.surrealdb import upsert_prototype


def _rows(payload: object) -> list[dict[str, object]]:
    if isinstance(payload, list):
        if payload and isinstance(payload[0], dict) and "result" in payload[0]:
            return payload[0]["result"]
        return payload
    if isinstance(payload, dict):
        return payload["result"]
    raise TypeError(f"unexpected query payload: {type(payload)!r}")


def test_run_batch_status_counts_sum_to_count(
    surreal_ephemeral: DbConfig,
) -> None:
    """Smoke: count=10 run produces 10 rows with non-NONE status."""
    db = connect(surreal_ephemeral)
    ensure_schema(db)

    report: BatchReport = run_batch(
        db=db,
        count=10,
        seed=0,
        iou_gate=0.90,
        cap=2,
    )
    total = (
        report.counts[Status.VERIFIED]
        + report.counts[Status.NEEDS_REVIEW]
        + report.counts[Status.UNSUPPORTED_OP]
        + report.counts[Status.FAILED_EXTRACTION]
    )
    assert total == report.selected
    assert total <= 10  # available buckets may be less than requested

    rows = _rows(db.query("SELECT char, status FROM glyph;"))
    assert len(rows) == total
    assert all(r["status"] in {s.value for s in Status} for r in rows)


def test_run_batch_skips_already_filled(
    surreal_ephemeral: DbConfig,
) -> None:
    db = connect(surreal_ephemeral)
    ensure_schema(db)
    # Pre-seed one char as "verified".
    db.query(
        "UPSERT type::record('glyph', '明') MERGE "
        "{ char: '明', status: 'verified', iou_mean: 1.0 };"
    )
    report = run_batch(db=db, count=5, seed=0, iou_gate=0.90, cap=2)
    # 明 must not reappear in the batch.
    assert "明" not in report.selected_chars


def test_run_batch_reproducible_per_seed(
    surreal_ephemeral: DbConfig,
) -> None:
    db = connect(surreal_ephemeral)
    ensure_schema(db)
    r1 = run_batch(db=db, count=5, seed=42, iou_gate=0.90, cap=2, dry_run=True)
    r2 = run_batch(db=db, count=5, seed=42, iou_gate=0.90, cap=2, dry_run=True)
    assert r1.selected_chars == r2.selected_chars


def test_run_batch_persists_variant_and_probe_counters(
    surreal_ephemeral: DbConfig,
    monkeypatch,
) -> None:
    db = connect(surreal_ephemeral)
    ensure_schema(db)
    monkeypatch.setattr(bulk_batch, "load_moe_4808", lambda: ["休"])
    monkeypatch.setattr(bulk_batch, "upsert_variant_of_edge", lambda *_args, **_kwargs: None)
    upsert_prototype(
        db,
        {
            "id": "proto:u4ebb",
            "name": "亻",
            "from_char": "亻",
            "source": {
                "kind": "mmh-extract",
                "from_char": "亻",
                "stroke_indices": [0, 1],
            },
            "stroke_indices": [0, 1],
            "roles": ["meaning"],
            "anchors": {},
        },
    )

    report = run_batch(db=db, count=1, seed=0, iou_gate=0.90, cap=2)

    assert report.selected_chars == ["休"]
    runs = _rows(db.query("SELECT * FROM extraction_run;"))
    assert len(runs) == 1
    assert runs[0]["variants_minted"] == 1
    assert runs[0]["canonical_probe_rejections"] == 1
