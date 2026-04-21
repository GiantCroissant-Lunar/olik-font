#!/usr/bin/env python3
"""Regenerate project/py/data/cjk-decomp.json from upstream.

Downloads cjk-decomp.txt from https://github.com/amake/cjk-decomp at a
pinned commit, parses every line into a structured entry, and writes
project/py/data/cjk-decomp.json + project/py/data/LICENSE-cjk-decomp.

Run with: `task data:regen-cjk-decomp`  (or `python3 scripts/regen-cjk-decomp.py`)

Pinning to a commit (instead of `master`) makes CI/reproducibility
deterministic. Bump the UPSTREAM_COMMIT constant when you want the
latest upstream; the JSON is re-committed with the new commit hash in
its `source` field so blame history is meaningful.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

UPSTREAM_REPO = "amake/cjk-decomp"
UPSTREAM_COMMIT = "c29b391fd6267e7a3541387e03a3dd60b1cd34d1"  # 2018-06-09
UPSTREAM_BASE = f"https://raw.githubusercontent.com/{UPSTREAM_REPO}/{UPSTREAM_COMMIT}"
UPSTREAM_TXT = f"{UPSTREAM_BASE}/cjk-decomp.txt"
UPSTREAM_LICENSE = f"{UPSTREAM_BASE}/LICENSE"

SCHEMA_VERSION = "0.1"
_LINE_RE = re.compile(r"^([^:]+):(?:([a-z][a-z0-9/]*|0)(?:\(([^)]*)\))?)")


def fetch(url: str) -> str:
    with urllib.request.urlopen(url, timeout=60) as resp:
        return resp.read().decode("utf-8")


def parse_text(raw: str) -> dict[str, dict]:
    entries: dict[str, dict] = {}
    for line_no, line in enumerate(raw.splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        m = _LINE_RE.match(stripped)
        if not m:
            raise ValueError(f"line {line_no}: unparseable {stripped!r}")
        char, op, args = m.group(1), m.group(2), m.group(3)
        if op is None or op == "0":
            entries[char] = {"operator": None, "components": []}
        else:
            parts = [p.strip() for p in (args or "").split(",") if p.strip()]
            entries[char] = {"operator": op, "components": parts}
    return entries


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out-dir",
        default=Path(__file__).resolve().parent.parent / "project" / "py" / "data",
        type=Path,
    )
    args = parser.parse_args()
    out_dir: Path = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"fetching {UPSTREAM_TXT}", file=sys.stderr)
    raw = fetch(UPSTREAM_TXT)
    print(f"parsing {len(raw.splitlines())} lines", file=sys.stderr)
    entries = parse_text(raw)
    print(f"{len(entries)} entries", file=sys.stderr)

    doc = {
        "schema_version": SCHEMA_VERSION,
        "source": {
            "upstream": f"https://github.com/{UPSTREAM_REPO}",
            "commit": UPSTREAM_COMMIT,
            "license": "Apache-2.0",
            "retrieved_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        },
        "entries": entries,
    }

    # Minified — 85k entries balloon to ~9 MB pretty-printed but compress to
    # ~3 MB on one line. Contributors can pretty-print ad-hoc with
    # `jq . cjk-decomp.json`. Schema validation is unaffected by formatting.
    json_path = out_dir / "cjk-decomp.json"
    json_path.write_text(
        json.dumps(doc, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {json_path} ({json_path.stat().st_size} bytes)", file=sys.stderr)

    print(f"fetching {UPSTREAM_LICENSE}", file=sys.stderr)
    license_text = fetch(UPSTREAM_LICENSE)
    license_path = out_dir / "LICENSE-cjk-decomp"
    license_path.write_text(
        "# Attribution for project/py/data/cjk-decomp.json\n"
        "#\n"
        "# This file is a structured JSON transform of cjk-decomp.txt from\n"
        f"#   {UPSTREAM_REPO}@{UPSTREAM_COMMIT}\n"
        "# The upstream data + this derivative are covered by Apache License 2.0.\n"
        "# The full upstream license text is reproduced below.\n"
        "# --------------------------------------------------------------------\n\n"
        + license_text,
        encoding="utf-8",
    )
    print(f"wrote {license_path}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
