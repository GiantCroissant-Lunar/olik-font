from __future__ import annotations

import sys
from pathlib import Path

import pytest

from olik_font.cli import main
from olik_font.sink.connection import DbConfig, connect
from olik_font.sink.schema import ensure_schema


def _set_env(monkeypatch: pytest.MonkeyPatch, cfg: DbConfig) -> None:
    monkeypatch.setenv("OLIK_DB_URL", cfg.url)
    monkeypatch.setenv("OLIK_DB_NS", cfg.namespace)
    monkeypatch.setenv("OLIK_DB_NAME", cfg.database)
    monkeypatch.setenv("OLIK_DB_USER", cfg.user)
    monkeypatch.setenv("OLIK_DB_PASS", cfg.password)


def test_style_subcommand_parses_and_invokes_batch(tmp_path: Path, monkeypatch) -> None:
    captured: dict[str, object] = {}

    class _Client:
        def __init__(self) -> None:
            captured["client_created"] = True

    def fake_stylize(*, chars, styles, out_dir, seeds_per_style, client, **kwargs):
        captured["chars"] = chars
        captured["styles"] = styles
        captured["out_dir"] = out_dir
        captured["seeds_per_style"] = seeds_per_style
        captured["client"] = client
        captured["glyph_records"] = kwargs["glyph_records"]
        captured["max_concurrent"] = kwargs["max_concurrent"]

        class _Report:
            requested = 24
            generated = 20
            skipped = 4
            failed = 0

        return _Report()

    monkeypatch.setattr("olik_font.cli.ComfyUIClient", _Client)
    monkeypatch.setattr("olik_font.cli.stylize", fake_stylize)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "olik",
            "style",
            "明",
            "清",
            "國",
            "森",
            "--styles",
            "ink-brush,aged-print,soft-watercolor",
            "--seeds",
            "2",
            "--out",
            str(tmp_path),
        ],
    )

    rc = main()

    assert rc == 0
    assert captured["client_created"] is True
    assert captured["chars"] == ["明", "清", "國", "森"]
    assert captured["styles"] == ["ink-brush", "aged-print", "soft-watercolor"]
    assert captured["out_dir"] == tmp_path
    assert captured["seeds_per_style"] == 2
    assert captured["glyph_records"] is None
    assert captured["max_concurrent"] == 1


def test_style_all_verified_loads_verified_rows_from_db(
    surreal_ephemeral: DbConfig,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_env(monkeypatch, surreal_ephemeral)
    db = connect(surreal_ephemeral)
    ensure_schema(db)
    db.query(
        "UPSERT type::record('glyph', '明') MERGE {"
        " char: '明', status: 'verified',"
        " coord_space: { width: 1024, height: 1024 },"
        " stroke_instances: [{ id: 's0', path: 'M 0 0 L 1 1', median: [[0, 0], [1, 1]] }]"
        " };"
    )
    db.query(
        "UPSERT type::record('glyph', '清') MERGE {"
        " char: '清', status: 'needs_review',"
        " coord_space: { width: 1024, height: 1024 },"
        " stroke_instances: [{ id: 's0', path: 'M 0 0 L 1 1', median: [[0, 0], [1, 1]] }]"
        " };"
    )
    db.query(
        "UPSERT type::record('glyph', '森') MERGE {"
        " char: '森', status: 'verified',"
        " coord_space: { width: 1024, height: 1024 },"
        " stroke_instances: [{ id: 's0', path: 'M 0 0 L 1 1', median: [[0, 0], [1, 1]] }]"
        " };"
    )

    captured: dict[str, object] = {}

    class _Client:
        def __init__(self) -> None:
            captured["client_created"] = True

    def fake_stylize(*, chars, styles, out_dir, seeds_per_style, client, **kwargs):
        captured["chars"] = chars
        captured["styles"] = styles
        captured["out_dir"] = out_dir
        captured["seeds_per_style"] = seeds_per_style
        captured["client"] = client
        captured["glyph_records"] = kwargs["glyph_records"]
        captured["max_concurrent"] = kwargs["max_concurrent"]

        class _Report:
            requested = 2
            generated = 2
            skipped = 0
            failed = 0

        return _Report()

    monkeypatch.setattr("olik_font.cli.ComfyUIClient", _Client)
    monkeypatch.setattr("olik_font.cli.stylize", fake_stylize)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "olik",
            "style",
            "--all-verified",
            "--styles",
            "ink-brush",
            "--seeds",
            "1",
            "--max-concurrent",
            "3",
            "--out",
            str(tmp_path),
        ],
    )

    rc = main()

    assert rc == 0
    assert captured["client_created"] is True
    assert captured["chars"] == ["明", "森"]
    assert captured["styles"] == ["ink-brush"]
    assert captured["out_dir"] == tmp_path
    assert captured["seeds_per_style"] == 1
    assert captured["max_concurrent"] == 3
    assert set(captured["glyph_records"]) == {"明", "森"}
