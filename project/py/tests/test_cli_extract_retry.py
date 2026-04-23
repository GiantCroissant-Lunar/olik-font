import sys
from collections import Counter

from olik_font.bulk.batch import BatchReport
from olik_font.bulk.status import Status
from olik_font.cli import main


class DummyDb:
    def __init__(self) -> None:
        self.deleted: list[str] = []

    def query(self, sql: str, params=None):
        if "SELECT char FROM glyph WHERE status = $s;" in sql:
            return [{"result": [{"char": "丁"}, {"char": "不"}]}]
        if "DELETE FROM glyph WHERE char = $c;" in sql:
            self.deleted.append(params["c"])
            return [{"result": []}]
        raise AssertionError(f"unexpected query: {sql}")


def test_extract_retry_chars_filters_selected_bucket(monkeypatch) -> None:
    db = DummyDb()
    seen: dict[str, object] = {}

    monkeypatch.setattr("olik_font.sink.connection.connect", lambda: db)
    monkeypatch.setattr("olik_font.sink.schema.ensure_schema", lambda _db: None)

    def fake_run_batch(*, db, count, seed, iou_gate, **_kwargs):
        seen["db"] = db
        seen["count"] = count
        seen["seed"] = seed
        seen["iou_gate"] = iou_gate
        return BatchReport(
            seed=seed,
            iou_gate=iou_gate,
            selected=count,
            selected_chars=["丁"],
            counts=Counter({Status.VERIFIED: 1}),
        )

    monkeypatch.setattr("olik_font.bulk.batch.run_batch", fake_run_batch)

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "olik",
            "extract",
            "retry",
            "--status",
            "failed_extraction",
            "--chars",
            "丁",
        ],
    )
    rc = main()

    assert rc == 0
    assert db.deleted == ["丁"]
    assert seen == {"db": db, "count": 1, "seed": 0, "iou_gate": 0.90}
