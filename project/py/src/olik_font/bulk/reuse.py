"""Prototype reuse policy with IoU-triggered context-variant fallback.

Canonical IDs: `proto:<component_name>` (e.g. `proto:tree` for 木).
Context variant IDs: `proto:<component_name>_in_<context_char>`
(e.g. `proto:tree_in_林`). The exact name stringification is the
responsibility of `name_to_slug`; callers never construct IDs themselves.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from olik_font.prototypes.extraction_plan import PrototypePlan

_SLUGS: dict[str, str] = {
    "木": "tree",
    "日": "sun",
    "月": "moon",
    "氵": "water_3dots",
    "囗": "enclosure_box",
    "或": "huo",
    "龶": "sheng",
    "青": "qing",
}


def name_to_slug(name: str) -> str:
    """Deterministic ASCII slug for a component name."""
    return _SLUGS.get(name, f"u{ord(name[0]):04x}")


def canonical_id(component_name: str) -> str:
    return f"proto:{name_to_slug(component_name)}"


def variant_id(component_name: str, context_char: str) -> str:
    return f"proto:{name_to_slug(component_name)}_in_{context_char}"


@dataclass(frozen=True)
class ProtoIndex:
    prototypes: list[PrototypePlan]

    @property
    def by_id(self) -> dict[str, PrototypePlan]:
        return {p.id: p for p in self.prototypes}

    def find_by_name(self, name: str) -> list[PrototypePlan]:
        return [p for p in self.prototypes if p.name == name]

    def canonical_for(self, component_name: str) -> PrototypePlan | None:
        cid = canonical_id(component_name)
        for p in self.prototypes:
            if p.id == cid:
                return p
        return None

    def variants_of(self, component_name: str) -> list[PrototypePlan]:
        """All `proto:X_in_Y` entries for a given component name `X`."""
        prefix = canonical_id(component_name) + "_in_"
        return [p for p in self.prototypes if p.id.startswith(prefix)]


@dataclass(frozen=True)
class ReuseDecision:
    chosen_id: str | None
    canonical_for_edge: str | None
    is_new_variant: bool = False
    is_new_canonical: bool = False
    cap_exceeded: bool = False


def decide_prototype(
    component_char: str,
    context_char: str,
    index: ProtoIndex,
    probe_iou: Callable[[PrototypePlan], float],
    gate: float,
    cap: int,
) -> ReuseDecision:
    """Decide which prototype a component should resolve to."""
    exact_variant = variant_id(component_char, context_char)
    for p in index.prototypes:
        if p.id == exact_variant:
            return ReuseDecision(chosen_id=exact_variant, canonical_for_edge=None)

    canonical = index.canonical_for(component_char)
    if canonical is None:
        return ReuseDecision(
            chosen_id=canonical_id(component_char),
            canonical_for_edge=None,
            is_new_canonical=True,
        )

    if probe_iou(canonical) >= gate:
        return ReuseDecision(chosen_id=canonical.id, canonical_for_edge=None)

    existing_variants = index.variants_of(component_char)
    if len(existing_variants) >= cap:
        return ReuseDecision(
            chosen_id=None,
            canonical_for_edge=None,
            cap_exceeded=True,
        )

    return ReuseDecision(
        chosen_id=exact_variant,
        canonical_for_edge=canonical.id,
        is_new_variant=True,
    )
