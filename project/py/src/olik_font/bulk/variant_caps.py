"""Per-component variant cap config."""

from __future__ import annotations

from dataclasses import dataclass
from fnmatch import fnmatchcase
from pathlib import Path

import yaml

_DATA_ROOT = Path(__file__).resolve().parents[3] / "data"
DEFAULT_VARIANT_CAPS = _DATA_ROOT / "variant_caps.yaml"
_GLOB_CHARS = frozenset("*?[")


def _parse_cap(key: str, value: object) -> int:
    if not isinstance(value, int):
        raise ValueError(f"variant cap for {key!r} must be an integer")
    if value < 0:
        raise ValueError(f"variant cap for {key!r} must be >= 0")
    return value


def _is_glob(pattern: str) -> bool:
    return any(ch in pattern for ch in _GLOB_CHARS)


@dataclass(frozen=True, slots=True)
class VariantCaps:
    exact: dict[str, int]
    patterns: tuple[tuple[str, int], ...]
    default: int

    def cap_for(self, component_name: str) -> int:
        if component_name in self.exact:
            return self.exact[component_name]
        for pattern, cap in self.patterns:
            if fnmatchcase(component_name, pattern):
                return cap
        return self.default


def load_variant_caps(path: Path = DEFAULT_VARIANT_CAPS) -> VariantCaps:
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise ValueError(f"failed to read {path}: expected mapping")

    default = _parse_cap("default", raw.get("default", 10))
    exact: dict[str, int] = {}
    patterns: list[tuple[str, int]] = []

    for key, value in raw.items():
        if key == "default":
            continue
        if not isinstance(key, str) or not key:
            raise ValueError(f"variant cap key must be a non-empty string: {key!r}")
        cap = _parse_cap(key, value)
        if _is_glob(key):
            patterns.append((key, cap))
        else:
            exact[key] = cap

    return VariantCaps(exact=exact, patterns=tuple(patterns), default=default)
