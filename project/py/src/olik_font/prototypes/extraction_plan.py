"""YAML loader for py/data/extraction_plan.yaml.

Hand-authored plan declares:
  - which MMH strokes belong to which prototype
  - per-glyph composition tree (preset + children + mode choices)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import yaml

Preset = Literal["left_right", "top_bottom", "enclose", "repeat_triangle"]
Mode = Literal["keep", "refine", "replace"]


@dataclass(frozen=True, slots=True)
class PrototypePlan:
    id: str
    name: str
    from_char: str
    stroke_indices: tuple[int, ...]
    roles: tuple[str, ...]
    anchors: dict[str, tuple[float, float]]


@dataclass(frozen=True, slots=True)
class GlyphNodePlan:
    prototype_ref: str
    mode: Mode = "keep"
    preset: Preset | None = None
    children: tuple[GlyphNodePlan, ...] = ()


@dataclass(frozen=True, slots=True)
class GlyphPlan:
    preset: Preset
    children: tuple[GlyphNodePlan, ...] = ()
    prototype_ref: str | None = None  # for repeat_triangle
    count: int | None = None  # for repeat_triangle


@dataclass(frozen=True, slots=True)
class ExtractionPlan:
    schema_version: str
    prototypes: tuple[PrototypePlan, ...]
    glyphs: dict[str, GlyphPlan] = field(default_factory=dict)

    @property
    def by_prototype_id(self) -> dict[str, PrototypePlan]:
        return {p.id: p for p in self.prototypes}


def _parse_node(obj: dict) -> GlyphNodePlan:
    return GlyphNodePlan(
        prototype_ref=obj["prototype_ref"],
        mode=obj.get("mode", "keep"),
        preset=obj.get("preset"),
        children=tuple(_parse_node(c) for c in obj.get("children", [])),
    )


def load_extraction_plan(path: Path) -> ExtractionPlan:
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, yaml.YAMLError) as exc:
        raise ValueError(f"failed to read {path}: {exc}") from exc
    prototypes = tuple(
        PrototypePlan(
            id=p["id"],
            name=p["name"],
            from_char=p["from_char"],
            stroke_indices=tuple(p["stroke_indices"]),
            roles=tuple(p.get("roles", [])),
            anchors={k: tuple(v) for k, v in p.get("anchors", {}).items()},
        )
        for p in raw["prototypes"]
    )
    glyphs: dict[str, GlyphPlan] = {}
    for char, g in raw.get("glyphs", {}).items():
        glyphs[char] = GlyphPlan(
            preset=g["preset"],
            children=tuple(_parse_node(c) for c in g.get("children", [])),
            prototype_ref=g.get("prototype_ref"),
            count=g.get("count"),
        )
    return ExtractionPlan(
        schema_version=raw["schema_version"],
        prototypes=prototypes,
        glyphs=glyphs,
    )
