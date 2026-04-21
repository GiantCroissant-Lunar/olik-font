"""Serialize PrototypeLibrary -> prototype-library.schema.json shape."""

from __future__ import annotations

from olik_font.types import PrototypeLibrary


def library_to_dict(lib: PrototypeLibrary) -> dict:
    protos: dict[str, dict] = {}
    for pid in lib.ids():
        p = lib[pid]
        protos[pid] = {
            "id": p.id,
            "name": p.name,
            "kind": p.kind,
            "source": dict(p.source),
            "canonical_bbox": list(p.canonical_bbox),
            "strokes": [
                {
                    "id": s.id,
                    "path": s.path,
                    "median": [list(pt) for pt in s.median],
                    "order": s.order,
                    "role": s.role,
                }
                for s in p.strokes
            ],
            "anchors": {k: list(v) for k, v in p.anchors.items()},
            "roles": list(p.roles),
            "refinement": {
                "mode": p.refinement_mode,
                "alternates": list(p.alternates),
            },
        }
    return {
        "schema_version": "0.1",
        "coord_space": {"width": 1024, "height": 1024, "origin": "top-left", "y_axis": "down"},
        "prototypes": protos,
        "edges": [],
    }
