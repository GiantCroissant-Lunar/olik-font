# project/py/tests/test_cjk_decomp_fetch.py
from pathlib import Path

import pytest

from olik_font.sources.cjk_decomp import fetch_cjk_decomp, load_cjk_decomp


def test_fetch_returns_existing_file_without_network(tmp_path: Path, monkeypatch):
    # pre-seed cache
    pre = tmp_path / "cjk-decomp.txt"
    pre.write_text("日:0\n月:0\n明:c(日,月)\n", encoding="utf-8")

    def boom(*a, **kw):
        raise AssertionError("network should not be called when cache is warm")

    monkeypatch.setattr("olik_font.sources.cjk_decomp._http_get", boom)
    out = fetch_cjk_decomp(tmp_path)
    assert out == pre
    assert load_cjk_decomp(out)["明"].components == ("日", "月")


def test_fetch_downloads_when_cache_missing(tmp_path: Path, monkeypatch):
    calls: list[str] = []

    def fake_get(url: str) -> bytes:
        calls.append(url)
        # Simulate the HanziJS wrapper with a backtick template literal
        body = "日:0\n月:0\n明:c(日,月)\n"
        return (f"module.exports = `{body}`;\n").encode()

    monkeypatch.setattr("olik_font.sources.cjk_decomp._http_get", fake_get)
    out = fetch_cjk_decomp(tmp_path)
    assert out.exists()
    assert len(calls) == 1
    # Re-running with warm cache = no extra HTTP
    fetch_cjk_decomp(tmp_path)
    assert len(calls) == 1

    table = load_cjk_decomp(out)
    assert table["明"].components == ("日", "月")
    assert table["日"].operator is None


def test_fetch_unwraps_quoted_string_literal(tmp_path: Path, monkeypatch):
    def fake_get(url: str) -> bytes:
        # Double-quoted wrapper with escaped newlines (not backtick)
        return b'module.exports = "\\u65e5:0\\n\\u6708:0\\n\\u660e:c(\\u65e5,\\u6708)\\n";\n'

    monkeypatch.setattr("olik_font.sources.cjk_decomp._http_get", fake_get)
    # The \uXXXX sequences in a JS string are passed through as literal text
    # bytes here (not decoded as unicode escapes by the wrapper regex). The
    # fetcher's responsibility is stripping the wrapper; it does NOT decode
    # \uXXXX escapes. Just assert the wrapper was stripped and the body is
    # consumable as UTF-8 text.
    out = fetch_cjk_decomp(tmp_path)
    assert out.read_text(encoding="utf-8").startswith("\\u65e5:0")


def test_fetch_http_error_raises(tmp_path: Path, monkeypatch):
    import requests

    def fail(url: str) -> bytes:
        resp = requests.models.Response()
        resp.status_code = 404
        resp.url = url
        resp.raise_for_status()
        return b""

    monkeypatch.setattr("olik_font.sources.cjk_decomp._http_get", fail)
    with pytest.raises(requests.HTTPError):
        fetch_cjk_decomp(tmp_path)
