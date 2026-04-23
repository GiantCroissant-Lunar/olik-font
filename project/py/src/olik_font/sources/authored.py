"""Sparse authored decomposition overrides."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

DEFAULT_ROOT = Path(__file__).resolve().parents[3] / "data" / "glyph_decomp"
_PROTO_REF_RE = re.compile(r"^proto:[A-Za-z0-9_]+$")


class AuthoredPartitionNode(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    prototype_ref: str
    mode: Literal["keep", "refine", "replace"] = "keep"
    source_stroke_indices: tuple[int, ...] | None = None
    children: tuple[AuthoredPartitionNode, ...] = ()
    replacement_proto_ref: str | None = None

    @field_validator("prototype_ref", "replacement_proto_ref")
    @classmethod
    def _validate_proto_ref(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not _PROTO_REF_RE.fullmatch(value):
            raise ValueError(f"invalid prototype ref: {value}")
        return value

    @field_validator("source_stroke_indices")
    @classmethod
    def _validate_source_stroke_indices(
        cls, value: tuple[int, ...] | None
    ) -> tuple[int, ...] | None:
        if value is None:
            return None
        if not value:
            raise ValueError("source_stroke_indices must not be empty")
        if any(index < 0 for index in value):
            raise ValueError("source_stroke_indices must be non-negative")
        return value

    @model_validator(mode="after")
    def _validate_replace_mode(self) -> AuthoredPartitionNode:
        if self.mode == "replace" and self.replacement_proto_ref is None:
            raise ValueError("replacement_proto_ref is required when mode='replace'")
        if self.mode != "replace" and self.replacement_proto_ref is not None:
            raise ValueError("replacement_proto_ref is only allowed when mode='replace'")
        return self


class AuthoredDecomposition(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["0.1"]
    char: str = Field(min_length=1, max_length=1)
    supersedes: Literal["mmh", "animcjk", "cjk-decomp"]
    rationale: str
    authored_by: str
    authored_at: datetime
    partition: tuple[AuthoredPartitionNode, ...]

    @field_validator("partition")
    @classmethod
    def _validate_partition(
        cls, value: tuple[AuthoredPartitionNode, ...]
    ) -> tuple[AuthoredPartitionNode, ...]:
        if not value:
            raise ValueError("partition must contain at least one node")
        return value


AuthoredPartitionNode.model_rebuild()


def load_authored(char: str, root: Path = DEFAULT_ROOT) -> AuthoredDecomposition | None:
    path = root / f"{char}.json"
    if not path.exists():
        return None
    try:
        authored = AuthoredDecomposition.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValidationError) as exc:
        raise ValueError(f"failed to validate {path}: {exc}") from exc
    if authored.char != char:
        raise ValueError(
            f"failed to validate {path}: char field {authored.char!r} != filename {char!r}"
        )
    return authored
