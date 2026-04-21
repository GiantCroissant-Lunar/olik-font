# project/py/tests/test_makemeahanzi_fetch.py
from pathlib import Path

import pytest

from olik_font.sources.makemeahanzi import fetch_mmh


def test_fetch_returns_existing_files_without_network(tmp_path: Path, monkeypatch):
    # pre-seed the cache with tiny files
    (tmp_path / "graphics.txt").write_text('{"character":"一","strokes":["M 0 0 L 10 0"],"medians":[[[0,0],[10,0]]]}\n')
    (tmp_path / "dictionary.txt").write_text('{"character":"一","definition":"one"}\n')

    def boom(*a, **kw):
        raise AssertionError("network should not be called when cache is warm")

    monkeypatch.setattr("olik_font.sources.makemeahanzi._http_get", boom)

    graphics, dictionary = fetch_mmh(tmp_path)
    assert graphics == tmp_path / "graphics.txt"
    assert dictionary == tmp_path / "dictionary.txt"


def test_fetch_downloads_when_cache_missing(tmp_path: Path, monkeypatch):
    calls: list[str] = []

    def fake_get(url: str) -> bytes:
        calls.append(url)
        if url.endswith("graphics.txt"):
            return '{"character":"一","strokes":["x"],"medians":[[[0,0]]]}\n'.encode("utf-8")
        if url.endswith("dictionary.txt"):
            return '{"character":"一","definition":"one"}\n'.encode("utf-8")
        raise AssertionError(f"unexpected url {url}")

    monkeypatch.setattr("olik_font.sources.makemeahanzi._http_get", fake_get)
    graphics, dictionary = fetch_mmh(tmp_path)

    assert graphics.exists()
    assert dictionary.exists()
    assert len(calls) == 2
    # second call should hit cache
    fetch_mmh(tmp_path)
    assert len(calls) == 2
