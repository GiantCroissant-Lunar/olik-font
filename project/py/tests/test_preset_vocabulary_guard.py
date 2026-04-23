from __future__ import annotations

import re
from pathlib import Path

PY_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]

SCAN_ROOTS = (
    PY_ROOT / "src",
    PY_ROOT / "tests",
    PY_ROOT / "data",
    REPO_ROOT / "project" / "ts" / "packages",
    REPO_ROOT / "project" / "ts" / "apps",
    REPO_ROOT / "project" / "schema" / "examples",
)

SKIP_DIRS = {"node_modules", "dist", ".venv", "__pycache__"}
SKIP_FILES = {
    Path(__file__).resolve(),
    PY_ROOT / "tests" / "test_extraction_plan_shape.py",
}
LITERAL_PATTERNS = (
    "preset:",
    "slot_bbox",
    "slot_weight",
    "_LEFT_RIGHT_WEIGHT",
    "_TOP_BOTTOM_WEIGHT",
    "_ENCLOSE_PADDING",
    "_REPEAT_TRIANGLE_SCALE",
)
WORD_PATTERN = re.compile(r"\b(left_right|top_bottom|repeat_triangle)\b")


def _iter_scan_files() -> tuple[Path, ...]:
    files: list[Path] = []
    for scan_root in SCAN_ROOTS:
        if not scan_root.exists():
            continue
        for path in scan_root.rglob("*"):
            if not path.is_file():
                continue
            if any(part in SKIP_DIRS for part in path.parts):
                continue
            if path in SKIP_FILES:
                continue
            if (
                scan_root.name == "packages"
                and "src" not in path.parts
                and "test" not in path.parts
            ):
                continue
            if (
                scan_root.name == "apps"
                and "src" not in path.parts
                and path.parts[-3:-1] != ("public", "data")
            ):
                continue
            files.append(path)
    return tuple(sorted(set(files)))


def _find_violations(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    violations = [pattern for pattern in LITERAL_PATTERNS if pattern in text]
    if WORD_PATTERN.search(text):
        violations.append("word-pattern")
    return violations


def test_preset_vocabulary_guard() -> None:
    files = _iter_scan_files()
    violations: dict[str, list[str]] = {}
    for path in files:
        matches = _find_violations(path)
        if matches:
            violations[path.relative_to(REPO_ROOT).as_posix()] = matches
    assert len(files) >= 30, f"expected to scan at least 30 files, scanned {len(files)}"
    assert not violations, f"found preset vocabulary in: {violations}"
