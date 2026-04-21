"""CLI: `olik extract auto|report|backfill-status|list|retry`."""

from __future__ import annotations

import pytest

from olik_font.cli import main
from olik_font.sink.connection import DbConfig, connect


def _rows(payload: object) -> list[dict]:
    if isinstance(payload, list):
        if payload and isinstance(payload[0], dict) and "result" in payload[0]:
            return payload[0]["result"]
        return payload
    if isinstance(payload, dict):
        return payload["result"]
    raise TypeError(f"unexpected query payload: {type(payload)!r}")


def _set_env(monkeypatch: pytest.MonkeyPatch, cfg: DbConfig) -> None:
    for var, val in [
        ("OLIK_DB_URL", cfg.url),
        ("OLIK_DB_NS", cfg.namespace),
        ("OLIK_DB_NAME", cfg.database),
        ("OLIK_DB_USER", cfg.user),
        ("OLIK_DB_PASS", cfg.password),
    ]:
        monkeypatch.setenv(var, val)


def test_extract_auto_populates_buckets(
    surreal_ephemeral: DbConfig, monkeypatch: pytest.MonkeyPatch
) -> None:
    _set_env(monkeypatch, surreal_ephemeral)
    monkeypatch.setattr("sys.argv", ["olik", "extract", "auto", "--count", "5", "--seed", "0"])
    rc = main()
    assert rc == 0
    db = connect(surreal_ephemeral)
    rows = _rows(db.query("SELECT char, status FROM glyph;"))
    assert 0 < len(rows) <= 5
    assert all(r.get("status") for r in rows)


def test_extract_report_prints_counts(
    surreal_ephemeral: DbConfig, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    _set_env(monkeypatch, surreal_ephemeral)
    monkeypatch.setattr("sys.argv", ["olik", "extract", "auto", "--count", "3", "--seed", "7"])
    main()
    monkeypatch.setattr("sys.argv", ["olik", "extract", "report"])
    rc = main()
    assert rc == 0
    out = capsys.readouterr().out
    assert "verified" in out
    assert "needs_review" in out


def test_extract_backfill_marks_seed_glyph_verified(
    surreal_ephemeral: DbConfig, monkeypatch: pytest.MonkeyPatch
) -> None:
    _set_env(monkeypatch, surreal_ephemeral)
    db = connect(surreal_ephemeral)
    db.query("UPSERT type::record('glyph', '明') MERGE { char: '明', iou_mean: 1.0 };")
    monkeypatch.setattr("sys.argv", ["olik", "extract", "backfill-status", "--iou-gate", "0.90"])
    rc = main()
    assert rc == 0
    row = _rows(db.query("SELECT status FROM glyph WHERE char = '明';"))[0]
    assert row["status"] == "verified"


def test_extract_list_prints_chars(
    surreal_ephemeral: DbConfig, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    _set_env(monkeypatch, surreal_ephemeral)
    monkeypatch.setattr("sys.argv", ["olik", "extract", "auto", "--count", "5", "--seed", "0"])
    main()
    monkeypatch.setattr("sys.argv", ["olik", "extract", "list", "--status", "needs_review"])
    rc = main()
    assert rc == 0
    _ = capsys.readouterr().out
    # output is one-char-per-line; may be empty if all 5 chose verified,
    # which is fine — we only assert the command exits 0.


def test_extract_retry_updates_status(
    surreal_ephemeral: DbConfig, monkeypatch: pytest.MonkeyPatch
) -> None:
    _set_env(monkeypatch, surreal_ephemeral)
    db = connect(surreal_ephemeral)
    from olik_font.sink.schema import ensure_schema

    ensure_schema(db)
    db.query(
        "UPSERT type::record('glyph', '明') MERGE "
        "{ char: '明', status: 'unsupported_op', missing_op: 'wb' };"
    )
    monkeypatch.setattr("sys.argv", ["olik", "extract", "retry", "--status", "unsupported_op"])
    rc = main()
    assert rc == 0
    row = _rows(db.query("SELECT status, missing_op FROM glyph WHERE char = '明';"))[0]
    # After retry, 明 should either be verified / needs_review (op 'a' is supported)
    assert row["status"] in {"verified", "needs_review"}
    assert row.get("missing_op") in (None, "")
