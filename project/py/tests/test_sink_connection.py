"""Connection factory reads env vars correctly."""

from __future__ import annotations

import pytest

from olik_font.sink.connection import DbConfig


def test_from_env_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in (
        "OLIK_DB_URL",
        "OLIK_DB_NS",
        "OLIK_DB_NAME",
        "OLIK_DB_USER",
        "OLIK_DB_PASS",
    ):
        monkeypatch.delenv(var, raising=False)
    cfg = DbConfig.from_env()
    assert cfg.url == "http://127.0.0.1:6480"
    assert cfg.namespace == "hanfont"
    assert cfg.database == "olik"
    assert cfg.user == "root"
    assert cfg.password == "root"


def test_from_env_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OLIK_DB_URL", "http://example:9999")
    monkeypatch.setenv("OLIK_DB_NS", "other_ns")
    monkeypatch.setenv("OLIK_DB_NAME", "other_db")
    cfg = DbConfig.from_env()
    assert cfg.url == "http://example:9999"
    assert cfg.namespace == "other_ns"
    assert cfg.database == "other_db"
