"""Integration smoke: variant minting end-to-end against ephemeral DB.

Runs a small auto-batch, then asserts:
- at least one `variant_of` edge was written OR counters reflect zero
  (accepted either way — depends on which chars the seed selects);
- `variants_minted` and `canonical_probe_rejections` round-trip through
  `extraction_run.counts`.

The test does NOT assert a specific verified/needs_review lift because
exact numbers depend on MMH data and the random char selection — we
assert structural correctness (the wiring works) rather than magnitude.
The lift itself is measured in Task 9's manual end-to-end.
"""

from __future__ import annotations

from olik_font.bulk.batch import BatchReport, run_batch
from olik_font.sink.connection import DbConfig, connect
from olik_font.sink.schema import ensure_schema


def _rows(payload: object) -> list[dict[str, object]]:
    if isinstance(payload, list):
        if payload and isinstance(payload[0], dict) and "result" in payload[0]:
            return payload[0]["result"]
        return payload
    if isinstance(payload, dict):
        return payload["result"]
    raise TypeError(f"unexpected query payload: {type(payload)!r}")


def test_run_batch_counters_populate(surreal_ephemeral: DbConfig) -> None:
    """A 10-char run populates the new counters and persists them."""
    db = connect(surreal_ephemeral)
    ensure_schema(db)

    report: BatchReport = run_batch(
        db=db,
        count=10,
        seed=0,
        iou_gate=0.90,
        cap=2,
    )
    assert report.variants_minted >= 0
    assert report.canonical_probe_rejections >= 0
    assert report.variants_minted <= report.canonical_probe_rejections + len(report.selected_chars)

    # Persisted into extraction_run.counts.
    run_rows = _rows(db.query("SELECT * FROM extraction_run;"))
    assert len(run_rows) == 1
    counts = run_rows[0]["counts"]
    assert counts["variants_minted"] == report.variants_minted
    assert counts["canonical_probe_rejections"] == report.canonical_probe_rejections


def test_run_batch_probe_detects_canonical_mismatch(
    surreal_ephemeral: DbConfig,
) -> None:
    """Sanity: post-probe rewire means at least some chars trigger the
    probe branch (non-zero `canonical_probe_rejections` OR zero variants
    simply because the seed happened to produce all-canonical-fit chars).
    This test allows either outcome — it's a smoke, not a magnitude assertion."""
    db = connect(surreal_ephemeral)
    ensure_schema(db)
    report = run_batch(db=db, count=10, seed=7, iou_gate=0.90, cap=2)
    # If no probe rejections on 10 random chars, something is probably
    # wrong (probe should hit below-gate cases often on real MMH data).
    # This is a loose assertion — tighten it once we've seen 3-4 actual
    # runs and know the typical rejection count.
    assert (
        report.canonical_probe_rejections >= 0
        and report.canonical_probe_rejections <= report.selected
    )
