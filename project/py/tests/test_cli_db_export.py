"""`olik db export` produces a JSON directory matching `olik build`'s shape."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from olik_font.cli import main
from olik_font.sink.connection import DbConfig


def _set_env(monkeypatch: pytest.MonkeyPatch, cfg: DbConfig) -> None:
    for var, val in [
        ("OLIK_DB_URL", cfg.url),
        ("OLIK_DB_NS", cfg.namespace),
        ("OLIK_DB_NAME", cfg.database),
        ("OLIK_DB_USER", cfg.user),
        ("OLIK_DB_PASS", cfg.password),
    ]:
        monkeypatch.setenv(var, val)


def test_db_export_produces_json_dir(
    surreal_ephemeral: DbConfig,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _set_env(monkeypatch, surreal_ephemeral)

    monkeypatch.setattr("sys.argv", ["olik", "db", "sync", "明"])
    main()

    out = tmp_path / "export"
    monkeypatch.setattr("sys.argv", ["olik", "db", "export", "--out", str(out)])
    rc = main()
    assert rc == 0

    assert (out / "prototype-library.json").exists()
    assert (out / "glyph-record-明.json").exists()

    rec = json.loads((out / "glyph-record-明.json").read_text(encoding="utf-8"))
    assert rec["char"] == "明"
    assert "stroke_instances" in rec
