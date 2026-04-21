# project/py/src/olik_font/sources/cjk_decomp.py
"""cjk-decomp source adapter.

Parses the cjk-decomp dataset (bundled with HanziJS, MIT-licensed) into a
character → (operator, components) table. Supports one-level and recursive
decomposition.

Data source (HanziJS by nieldlr): `lib/data/cjk-decomp.txt.js` — a JS
module whose body is a template-literal string of the raw cjk-decomp.txt
lines. Two acquisition paths:
  • `fetch_cjk_decomp(cache_dir)` — portable: downloads from GitHub raw
    and extracts into a plain-text file. No local clone required.
    Matches the MMH fetcher's idempotent cache-hit behavior.
  • `extract_from_hanzijs(js_path, out_path)` — escape hatch: if a local
    HanziJS clone is available (e.g. under `ref-projects/`), extract
    from that file directly. Kept for offline / deterministic runs.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import requests

CJK_DECOMP_JS_URL = (
    "https://raw.githubusercontent.com/nieldlr/hanzi/master/lib/data/cjk-decomp.txt.js"
)

_LINE_RE = re.compile(r"^([^:]+):(?:([a-z][a-z0-9/]*|0)(?:\(([^)]*)\))?)")
_JS_WRAPPER_RE = re.compile(
    r"""module\.exports\s*=\s*(?P<quote>[`"'])(?P<body>.*?)(?P=quote)\s*;?\s*$""", re.DOTALL
)


@dataclass(frozen=True, slots=True)
class CjkDecompEntry:
    char: str
    operator: str | None  # single-letter operator; None means atomic
    components: tuple[str, ...]


def load_cjk_decomp(path: Path) -> dict[str, CjkDecompEntry]:
    """Parse a plain cjk-decomp.txt file into a char → entry table."""
    out: dict[str, CjkDecompEntry] = {}
    for line_no, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = _LINE_RE.match(line)
        if not m:
            raise ValueError(f"{path}:{line_no}: unparseable line: {line!r}")
        char, op, args = m.group(1), m.group(2), m.group(3)
        if op is None or op == "0":
            out[char] = CjkDecompEntry(char=char, operator=None, components=())
        else:
            parts = tuple(p.strip() for p in (args or "").split(",") if p.strip())
            out[char] = CjkDecompEntry(char=char, operator=op, components=parts)
    return out


def _extract_body(raw: str, source_label: str) -> str:
    m = _JS_WRAPPER_RE.search(raw)
    if not m:
        raise ValueError(f"{source_label}: no module.exports string literal found")
    body = m.group("body")
    # Template literals (backtick) are already plain text; quoted strings may
    # use \n, \\, etc. — apply a minimal unescape only for non-backtick quotes.
    if m.group("quote") != "`":
        body = body.replace("\\n", "\n").replace("\\\\", "\\")
    return body


def extract_from_hanzijs(js_path: Path, out_path: Path) -> Path:
    """Strip the `module.exports = "..."` wrapper from a local HanziJS file
    and write plain text. Use this when a local HanziJS clone is available."""
    raw = js_path.read_text(encoding="utf-8")
    body = _extract_body(raw, source_label=str(js_path))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(body, encoding="utf-8")
    return out_path


def _http_get(url: str) -> bytes:
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    return resp.content


def fetch_cjk_decomp(cache_dir: Path) -> Path:
    """Ensure `cjk-decomp.txt` exists in cache_dir, downloading from HanziJS
    upstream on GitHub and stripping the JS wrapper. Idempotent — re-running
    with a warm cache is a no-op."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    out_path = cache_dir / "cjk-decomp.txt"
    if out_path.exists():
        return out_path
    raw_bytes = _http_get(CJK_DECOMP_JS_URL)
    body = _extract_body(raw_bytes.decode("utf-8"), source_label=CJK_DECOMP_JS_URL)
    out_path.write_text(body, encoding="utf-8")
    return out_path


def decompose_once(table: dict[str, CjkDecompEntry], char: str) -> tuple[str, ...]:
    """One-level decomposition. Atomic chars return a 1-tuple (char,)."""
    entry = table[char]
    if entry.operator is None:
        return (char,)
    return entry.components


def decompose_recursive(
    table: dict[str, CjkDecompEntry],
    char: str,
    _seen: frozenset[str] = frozenset(),
) -> tuple[str, ...]:
    """Recursive decomposition down to atomic leaves. Cycle-safe."""
    if char in _seen:
        return (char,)
    entry = table.get(char)
    if entry is None or entry.operator is None:
        return (char,)
    out: list[str] = []
    next_seen = _seen | {char}
    for sub in entry.components:
        out.extend(decompose_recursive(table, sub, next_seen))
    return tuple(out)
