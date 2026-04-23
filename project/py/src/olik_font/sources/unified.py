"""Unified authored + MMH + animCJK + cjk-decomp source lookup."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from olik_font.bulk.mmh_partition import nested_partition, top_level_partition
from olik_font.sources.animcjk import load_animcjk_dictionary, load_animcjk_graphics
from olik_font.sources.authored import DEFAULT_ROOT as DEFAULT_AUTHORED_ROOT
from olik_font.sources.authored import AuthoredDecomposition, AuthoredPartitionNode, load_authored
from olik_font.sources.cjk_decomp import DEFAULT_CJK_OVERRIDES, DEFAULT_CJK_PATH, load_cjk_entries
from olik_font.sources.makemeahanzi import (
    MmhChar,
    MmhDictEntry,
    fetch_mmh,
    load_mmh_dictionary,
    load_mmh_graphics,
)

SourceMissLogger = Callable[[str, str], None]
DecompositionSource = Literal["authored", "animcjk", "mmh", "cjk-decomp"]


@dataclass(frozen=True, slots=True)
class PartitionNode:
    component: str | None = None
    prototype_ref: str | None = None
    mode: Literal["keep", "refine", "replace"] = "keep"
    source_stroke_indices: tuple[int, ...] | None = None
    children: tuple[PartitionNode, ...] = ()
    replacement_proto_ref: str | None = None


@dataclass(frozen=True, slots=True)
class Decomposition:
    partition: tuple[PartitionNode, ...]
    source: DecompositionSource
    confidence: float


@dataclass(frozen=True, slots=True)
class UnifiedLookup:
    mmh_graphics: dict[str, MmhChar]
    mmh_dictionary: dict[str, MmhDictEntry]
    animcjk_graphics: dict[str, MmhChar]
    animcjk_dictionary: dict[str, MmhDictEntry]
    cjk_entries: dict[str, dict[str, Any]]
    authored_root: Path = DEFAULT_AUTHORED_ROOT
    on_miss: SourceMissLogger | None = None

    def char_graphics_lookup(self, char: str) -> MmhChar | None:
        entry = self.mmh_graphics.get(char)
        if entry is not None:
            return entry
        entry = self.animcjk_graphics.get(char)
        if entry is not None:
            return entry
        if self.on_miss is not None:
            self.on_miss("graphics", char)
        return None

    def char_dictionary_lookup(self, char: str) -> MmhDictEntry | None:
        entry = self.mmh_dictionary.get(char)
        if entry is not None:
            return entry
        entry = self.animcjk_dictionary.get(char)
        if entry is not None:
            return entry
        if self.on_miss is not None:
            self.on_miss("dictionary", char)
        return None

    def merged_graphics(self) -> dict[str, MmhChar]:
        return {**self.animcjk_graphics, **self.mmh_graphics}

    def merged_dictionary(self) -> dict[str, MmhDictEntry]:
        return {**self.animcjk_dictionary, **self.mmh_dictionary}

    def char_decomposition_lookup(self, char: str) -> Decomposition | None:
        authored = load_authored(char, root=self.authored_root)
        if authored is not None:
            return _decomposition_from_authored(authored)

        if char in self.animcjk_dictionary:
            decomp = _decomposition_from_component_tree(
                self.cjk_entries.get(char),
                self.animcjk_dictionary[char].matches,
                source="animcjk",
            )
            if decomp is not None:
                return decomp

        if char in self.mmh_dictionary:
            decomp = _decomposition_from_component_tree(
                self.cjk_entries.get(char),
                self.mmh_dictionary[char].matches,
                source="mmh",
            )
            if decomp is not None:
                return decomp

        decomp = _decomposition_from_component_tree(
            self.cjk_entries.get(char),
            None,
            source="cjk-decomp",
        )
        if decomp is not None:
            return decomp

        if self.on_miss is not None:
            self.on_miss("decomposition", char)
        return None


def _partition_for_prefix(
    matches: list[list[int] | None] | None,
    prefix: tuple[int, ...],
) -> list[list[int]] | None:
    if not prefix:
        return top_level_partition(matches)
    return nested_partition(matches, path_prefix=prefix)


def _leaf_indices(
    matches: list[list[int] | None] | None,
    path: tuple[int, ...],
) -> tuple[int, ...] | None:
    if not path:
        return None
    groups = _partition_for_prefix(matches, path[:-1])
    if groups is None or path[-1] >= len(groups):
        return None
    return tuple(groups[path[-1]])


def _auto_partition_nodes(
    component_tree: list[dict[str, Any]],
    matches: list[list[int] | None] | None,
    path: tuple[int, ...] = (),
) -> tuple[PartitionNode, ...]:
    nodes: list[PartitionNode] = []
    for index, raw_node in enumerate(component_tree):
        child_path = (*path, index)
        raw_children = raw_node.get("components", [])
        children = (
            _auto_partition_nodes(raw_children, matches, child_path)
            if isinstance(raw_children, list) and raw_children
            else ()
        )
        nodes.append(
            PartitionNode(
                component=str(raw_node.get("char") or ""),
                mode="refine" if children else "keep",
                source_stroke_indices=None if children else _leaf_indices(matches, child_path),
                children=children,
            )
        )
    return tuple(nodes)


def _decomposition_from_component_tree(
    entry: dict[str, Any] | None,
    matches: list[list[int] | None] | None,
    *,
    source: DecompositionSource,
) -> Decomposition | None:
    if entry is None:
        return None
    raw_tree = entry.get("component_tree")
    if not isinstance(raw_tree, list) or not raw_tree:
        raw_components = entry.get("components", [])
        if not isinstance(raw_components, list) or not raw_components:
            return None
        raw_tree = [{"char": str(component), "components": []} for component in raw_components]
    return Decomposition(
        partition=_auto_partition_nodes(raw_tree, matches),
        source=source,
        confidence=1.0,
    )


def _authored_partition_nodes(
    nodes: tuple[AuthoredPartitionNode, ...],
) -> tuple[PartitionNode, ...]:
    return tuple(
        PartitionNode(
            prototype_ref=node.prototype_ref,
            mode=node.mode,
            source_stroke_indices=node.source_stroke_indices,
            children=_authored_partition_nodes(node.children),
            replacement_proto_ref=node.replacement_proto_ref,
        )
        for node in nodes
    )


def _decomposition_from_authored(authored: AuthoredDecomposition) -> Decomposition:
    return Decomposition(
        partition=_authored_partition_nodes(authored.partition),
        source="authored",
        confidence=1.0,
    )


def load_unified_lookup(
    mmh_dir: Path,
    animcjk_dir: Path,
    *,
    cjk_path: Path = DEFAULT_CJK_PATH,
    overrides_path: Path = DEFAULT_CJK_OVERRIDES,
    authored_root: Path = DEFAULT_AUTHORED_ROOT,
    on_miss: SourceMissLogger | None = None,
) -> UnifiedLookup:
    graphics_path, dictionary_path = fetch_mmh(mmh_dir)
    anim_graphics_path = animcjk_dir / "graphicsZhHant.txt"
    anim_dictionary_path = animcjk_dir / "dictionaryZhHant.txt"

    animcjk_graphics = (
        load_animcjk_graphics(anim_graphics_path) if anim_graphics_path.exists() else {}
    )
    animcjk_dictionary = (
        load_animcjk_dictionary(anim_dictionary_path) if anim_dictionary_path.exists() else {}
    )

    return UnifiedLookup(
        mmh_graphics=load_mmh_graphics(graphics_path),
        mmh_dictionary=load_mmh_dictionary(dictionary_path),
        animcjk_graphics=animcjk_graphics,
        animcjk_dictionary=animcjk_dictionary,
        cjk_entries=load_cjk_entries(cjk_path, overrides_path=overrides_path),
        authored_root=authored_root,
        on_miss=on_miss,
    )
