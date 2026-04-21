"""Carve MMH strokes into reusable Prototype records.

Each PrototypePlan declares stroke indices within an MMH character. We
select those strokes, compute their union bbox, and normalize geometry
into the prototype's local 1024² canonical space.
"""

from __future__ import annotations

from olik_font.geom import apply_affine_to_median, normalize_paths_to_canonical
from olik_font.prototypes.extraction_plan import ExtractionPlan, PrototypePlan
from olik_font.sources.makemeahanzi import MmhChar
from olik_font.types import Prototype, PrototypeLibrary, Stroke

CANONICAL_BBOX = (0.0, 0.0, 1024.0, 1024.0)


def extract_prototype(plan: PrototypePlan, mmh_char: MmhChar) -> Prototype:
    if mmh_char is None:
        raise KeyError(f"MMH char required for {plan.id}")
    if mmh_char.character != plan.from_char:
        raise ValueError(f"{plan.id} expects from_char {plan.from_char}, got {mmh_char.character}")
    selected_paths = tuple(mmh_char.strokes[i] for i in plan.stroke_indices)
    selected_medians = tuple(
        tuple((float(x), float(y)) for x, y in mmh_char.medians[i]) for i in plan.stroke_indices
    )

    normalized_paths, fwd = normalize_paths_to_canonical(selected_paths, CANONICAL_BBOX)
    normalized_medians = tuple(apply_affine_to_median(fwd, m) for m in selected_medians)

    strokes = tuple(
        Stroke(
            id=f"s{idx}",
            path=path,
            median=med,
            order=idx,
            role=_infer_role_from_median(med),
        )
        for idx, (path, med) in enumerate(zip(normalized_paths, normalized_medians, strict=False))
    )

    return Prototype(
        id=plan.id,
        name=plan.name,
        kind="component",
        canonical_bbox=CANONICAL_BBOX,
        strokes=strokes,
        anchors={k: tuple(v) for k, v in plan.anchors.items()},
        roles=plan.roles,
        refinement_mode="keep",
        source={
            "kind": "mmh-extract",
            "from_char": plan.from_char,
            "stroke_indices": list(plan.stroke_indices),
        },
    )


def extract_all_prototypes(
    plan: ExtractionPlan,
    mmh_chars: dict[str, MmhChar],
    lib: PrototypeLibrary,
) -> None:
    for pp in plan.prototypes:
        mmh = mmh_chars[pp.from_char]
        lib.add(extract_prototype(pp, mmh))


def _infer_role_from_median(median: tuple[tuple[float, float], ...]) -> str:
    """Coarse role inference: horizontal vs vertical vs dot vs other.

    Good enough for z-layer assignment (roles map to layer bases); Plan 03
    compose code reads this field but doesn't require fine-grained roles.
    """
    if len(median) < 2:
        return "dot"
    (x0, y0), (x1, y1) = median[0], median[-1]
    dx, dy = abs(x1 - x0), abs(y1 - y0)
    if dx < 50 and dy < 50:
        return "dot"
    if dy < dx * 0.3:
        return "horizontal"
    if dx < dy * 0.3:
        return "vertical"
    return "other"
