"""Plan 14 Task 5: MMH radical + etymology import."""

from __future__ import annotations

from pathlib import Path

import pytest

from olik_font.cli import main
from olik_font.sink.connection import DbConfig, connect
from olik_font.sources.makemeahanzi import (
    etymology as mmh_etymology,
)
from olik_font.sources.makemeahanzi import (
    fetch_mmh,
    load_mmh_dictionary,
)
from olik_font.sources.makemeahanzi import (
    radical as mmh_radical,
)

ROOT = Path(__file__).resolve().parents[1]
MMH_DIR = ROOT / "data" / "mmh"
MMH_GRAPHICS = MMH_DIR / "graphics.txt"

pytestmark = pytest.mark.skipif(not MMH_GRAPHICS.exists(), reason="run Plan 01 Task 4 first")


def _set_env(monkeypatch: pytest.MonkeyPatch, cfg: DbConfig) -> None:
    monkeypatch.setenv("OLIK_DB_URL", cfg.url)
    monkeypatch.setenv("OLIK_DB_NS", cfg.namespace)
    monkeypatch.setenv("OLIK_DB_NAME", cfg.database)
    monkeypatch.setenv("OLIK_DB_USER", cfg.user)
    monkeypatch.setenv("OLIK_DB_PASS", cfg.password)


def _rows(payload: object) -> list[dict]:
    if isinstance(payload, list):
        if payload and isinstance(payload[0], dict) and "result" in payload[0]:
            return payload[0]["result"]
        return payload
    if isinstance(payload, dict):
        return payload["result"]
    raise TypeError(f"unexpected query payload: {type(payload)!r}")


def _record_key(value: object, table: str) -> str:
    if getattr(value, "table_name", None) == table and isinstance(getattr(value, "id", None), str):
        return value.id
    text = str(value)
    prefix = f"{table}:"
    if text.startswith(prefix):
        return text[len(prefix) :].removeprefix("⟨").removesuffix("⟩")
    return text


def test_mmh_radical_for_ming() -> None:
    _, dictionary_path = fetch_mmh(MMH_DIR)
    mmh_dictionary = load_mmh_dictionary(dictionary_path)
    assert mmh_radical("明", dictionary=mmh_dictionary) == "日"


def test_mmh_etymology_for_ming() -> None:
    _, dictionary_path = fetch_mmh(MMH_DIR)
    mmh_dictionary = load_mmh_dictionary(dictionary_path)
    assert mmh_etymology("明", dictionary=mmh_dictionary) == "ideographic"


def test_db_sync_writes_has_kangxi_and_etymology(
    surreal_ephemeral: DbConfig,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_env(monkeypatch, surreal_ephemeral)
    monkeypatch.setattr("sys.argv", ["olik", "db", "sync", "明"])
    rc = main()
    assert rc == 0

    db = connect(surreal_ephemeral)
    glyph_rows = _rows(db.query("SELECT char, radical, etymology FROM glyph WHERE char = '明';"))
    assert glyph_rows == [{"char": "明", "radical": "日", "etymology": "ideographic"}]

    edge_rows = _rows(
        db.query(
            "SELECT out FROM has_kangxi WHERE in = type::record('glyph', $char);",
            {"char": "明"},
        )
    )
    assert len(edge_rows) == 1
    assert _record_key(edge_rows[0]["out"], "prototype") == "proto:kangxi_u65e5"


def test_extract_auto_populates_kangxi_and_etymology_for_most_of_100_chars(
    surreal_ephemeral: DbConfig,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_env(monkeypatch, surreal_ephemeral)
    monkeypatch.setattr("sys.argv", ["olik", "extract", "auto", "--count", "100", "--seed", "0"])
    rc = main()
    assert rc == 0

    db = connect(surreal_ephemeral)
    glyph_rows = _rows(db.query("SELECT count() AS count FROM glyph GROUP ALL;"))
    kangxi_rows = _rows(db.query("SELECT count() AS count FROM has_kangxi GROUP ALL;"))
    etymology_rows = _rows(
        db.query("SELECT count() AS count FROM glyph WHERE etymology != NONE GROUP ALL;")
    )

    assert int(glyph_rows[0]["count"]) == 100
    assert int(kangxi_rows[0]["count"]) >= 90
    assert int(etymology_rows[0]["count"]) >= 60
