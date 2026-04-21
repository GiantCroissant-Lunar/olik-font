"""Resolved constraint primitives emitted by presets.

Shape: immutable dataclasses, serialized to JSON via `as_dict`. The JSON form
matches the `constraints[]` shape in glyph-record.schema.json.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AlignX:
    targets: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class AlignY:
    targets: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class OrderX:
    before: str
    after: str


@dataclass(frozen=True, slots=True)
class OrderY:
    above: str
    below: str


@dataclass(frozen=True, slots=True)
class AnchorDistance:
    from_: str
    to: str
    value: float


@dataclass(frozen=True, slots=True)
class Inside:
    target: str
    frame: str
    padding: float


@dataclass(frozen=True, slots=True)
class AvoidOverlap:
    a: str
    b: str
    padding: float


@dataclass(frozen=True, slots=True)
class Repeat:
    prototype_ref: str
    count: int
    layout_hint: str


Primitive = AlignX | AlignY | OrderX | OrderY | AnchorDistance | Inside | AvoidOverlap | Repeat


def as_dict(p: Primitive) -> dict:
    if isinstance(p, AlignX):
        return {"kind": "align_x", "targets": list(p.targets)}
    if isinstance(p, AlignY):
        return {"kind": "align_y", "targets": list(p.targets)}
    if isinstance(p, OrderX):
        return {"kind": "order_x", "before": p.before, "after": p.after}
    if isinstance(p, OrderY):
        return {"kind": "order_y", "above": p.above, "below": p.below}
    if isinstance(p, AnchorDistance):
        return {"kind": "anchor_distance", "from": p.from_, "to": p.to, "value": p.value}
    if isinstance(p, Inside):
        return {"kind": "inside", "target": p.target, "frame": p.frame, "padding": p.padding}
    if isinstance(p, AvoidOverlap):
        return {"kind": "avoid_overlap", "a": p.a, "b": p.b, "padding": p.padding}
    if isinstance(p, Repeat):
        return {
            "kind": "repeat",
            "prototype_ref": p.prototype_ref,
            "count": p.count,
            "layout_hint": p.layout_hint,
        }
    raise TypeError(f"not a constraint primitive: {type(p).__name__}")
