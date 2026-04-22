from __future__ import annotations

import sys
from pathlib import Path

from olik_font.cli import main


def test_style_subcommand_parses_and_invokes_batch(tmp_path: Path, monkeypatch) -> None:
    captured: dict[str, object] = {}

    class _Client:
        def __init__(self) -> None:
            captured["client_created"] = True

    def fake_stylize(*, chars, styles, out_dir, seeds_per_style, client):
        captured["chars"] = chars
        captured["styles"] = styles
        captured["out_dir"] = out_dir
        captured["seeds_per_style"] = seeds_per_style
        captured["client"] = client

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
