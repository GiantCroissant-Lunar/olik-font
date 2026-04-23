"""`olik db sync 明` populates the DB; `db reset` drops + recreates."""

from __future__ import annotations

import pytest

from olik_font.cli import main
from olik_font.sink.connection import DbConfig, connect


def _set_env(monkeypatch: pytest.MonkeyPatch, cfg: DbConfig) -> None:
    monkeypatch.setenv("OLIK_DB_URL", cfg.url)
    monkeypatch.setenv("OLIK_DB_NS", cfg.namespace)
    monkeypatch.setenv("OLIK_DB_NAME", cfg.database)
    monkeypatch.setenv("OLIK_DB_USER", cfg.user)
    monkeypatch.setenv("OLIK_DB_PASS", cfg.password)


def _rows(payload: object) -> list[dict[str, object]]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        return payload["result"]
    raise TypeError(f"unexpected query payload: {type(payload)!r}")


def _table_names(info: object) -> set[str]:
    if isinstance(info, list):
        return set(info[0]["result"]["tables"].keys())
    if isinstance(info, dict):
        return set(info["tables"].keys())
    raise TypeError(f"unexpected INFO FOR DB payload: {type(info)!r}")


def test_db_sync_writes_glyph(
    surreal_ephemeral: DbConfig,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_env(monkeypatch, surreal_ephemeral)
    monkeypatch.setattr("sys.argv", ["olik", "db", "sync", "明"])
    rc = main()
    assert rc == 0

    db = connect(surreal_ephemeral)
    row = _rows(db.query("SELECT char, stroke_count FROM glyph WHERE char = '明';"))
    assert len(row) == 1
    assert row[0]["char"] == "明"
    assert row[0]["stroke_count"] >= 1
    productive = _rows(
        db.query("SELECT count() AS count FROM prototype WHERE productive_count > 0 GROUP ALL;")
    )
    assert productive[0]["count"] >= 1


def test_db_reset_clears_and_recreates(
    surreal_ephemeral: DbConfig,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_env(monkeypatch, surreal_ephemeral)
    monkeypatch.setattr("sys.argv", ["olik", "db", "sync", "明"])
    main()

    monkeypatch.setattr("sys.argv", ["olik", "db", "reset", "--yes"])
    rc = main()
    assert rc == 0

    db = connect(surreal_ephemeral)
    rows = _rows(db.query("SELECT * FROM glyph;"))
    assert rows == []
    info = db.query("INFO FOR DB;")
    assert "glyph" in _table_names(info)
