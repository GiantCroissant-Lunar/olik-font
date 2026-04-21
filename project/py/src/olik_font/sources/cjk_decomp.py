# project/py/src/olik_font/sources/cjk_decomp.py
"""cjk-decomp source adapter.

Parses the cjk-decomp.txt dataset bundled with HanziJS into a character →
(operator, components) table. Supports one-level and recursive decomposition.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

# A bundled copy lives at:
#   ref-projects/hanzi/lib/data/cjk-decomp.txt.js
# which is a JS module exporting the raw text. We provide an extractor.

_LINE_RE = re.compile(r"^([^:]+):(?:([a-z][a-z0-9/]*|0)(?:\(([^)]*)\))?)")
_JS_WRAPPER_RE = re.compile(r"""module\.exports\s*=\s*(?P<quote>[`"'])(?P<body>.*?)(?P=quote)\s*;?\s*$""", re.DOTALL)


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


def extract_from_hanzijs(js_path: Path, out_path: Path) -> Path:
    """Strip the `module.exports = "..."` wrapper and write plain text."""
    raw = js_path.read_text(encoding="utf-8")
    m = _JS_WRAPPER_RE.search(raw)
    if not m:
        raise ValueError(f"{js_path}: no module.exports string literal found")
    body = m.group("body")
    # Template literals (backtick) are already plain text; quoted strings may
    # use \n, \\, etc. — apply a minimal unescape only for non-backtick quotes.
    if m.group("quote") != "`":
        body = body.replace("\\n", "\n").replace("\\\\", "\\")
    out_path.parent.mkdir(parents=True, exist_ok=True)
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
