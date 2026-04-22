"""Shared immutable dataclasses for the olik-font pipeline.

All types are frozen + slotted. Containers use tuples, not lists, so equality
and hashing behave predictably across the pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

Point = tuple[float, float]
BBox = tuple[float, float, float, float]  # (x0, y0, x1, y1)
Mode = Literal["keep", "refine", "replace"]
Role = Literal["horizontal", "vertical", "dot", "hook", "slash", "backslash", "fold", "other"]


@dataclass(frozen=True, slots=True)
class Affine:
    translate: Point = (0.0, 0.0)
    scale: Point = (1.0, 1.0)
    rotate: float = 0.0
    shear: Point = (0.0, 0.0)

    @classmethod
    def identity(cls) -> Affine:
        return cls()


@dataclass(frozen=True, slots=True)
class AnchorBinding:
    from_: str  # "<instance_id>.<anchor_name>"
    to: str
    distance: float | None = None


@dataclass(frozen=True, slots=True)
class Stroke:
    id: str
    path: str  # SVG path d-string
    median: tuple[Point, ...]
    order: int
    role: Role


@dataclass(frozen=True, slots=True)
class Prototype:
    id: str
    name: str
    kind: Literal["component", "stroke", "group"]
    canonical_bbox: BBox
    strokes: tuple[Stroke, ...]
    anchors: dict[str, Point]
    roles: tuple[Literal["meaning", "sound", "iconic", "distinguishing", "unknown"], ...]
    refinement_mode: Mode
    alternates: tuple[str, ...] = ()
    source: dict[str, object] = field(default_factory=dict)


@dataclass(slots=True)
class PrototypeLibrary:
    _by_id: dict[str, Prototype] = field(default_factory=dict)

    def add(self, p: Prototype) -> None:
        if p.id in self._by_id:
            raise ValueError(f"duplicate prototype id: {p.id}")
        self._by_id[p.id] = p

    def __getitem__(self, proto_id: str) -> Prototype:
        return self._by_id[proto_id]

    def contains(self, proto_id: str) -> bool:
        return proto_id in self._by_id

    def ids(self) -> tuple[str, ...]:
        return tuple(self._by_id.keys())

    def __len__(self) -> int:
        return len(self._by_id)


@dataclass(frozen=True, slots=True)
class InstancePlacement:
    instance_id: str
    prototype_ref: str
    transform: Affine | None
    source_stroke_indices: tuple[int, ...] | None = None
    anchor_bindings: tuple[AnchorBinding, ...] = ()
    mode: Mode = "keep"
    depth: int = 0
    children: tuple[InstancePlacement, ...] = ()
    input_adapter: str = "direct"
    decomp_source: dict[str, object] = field(default_factory=dict)
