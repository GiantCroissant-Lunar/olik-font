from __future__ import annotations

import json
import math
from copy import deepcopy
from pathlib import Path

from olik_font.prototypes.geom_stats import centroid_distance, glyph_centroid, inertia_spread

ROOT = Path(__file__).resolve().parents[2]
MING_RECORD = ROOT / "schema" / "examples" / "glyph-record-明.json"


def test_ming_centroid_is_near_canvas_center() -> None:
    record = json.loads(MING_RECORD.read_text(encoding="utf-8"))
    cx, cy = glyph_centroid(record)
    assert 420.0 <= cx <= 560.0
    assert 400.0 <= cy <= 560.0


def test_ming_inertia_is_finite_and_non_zero() -> None:
    record = json.loads(MING_RECORD.read_text(encoding="utf-8"))
    spread = inertia_spread(record)
    assert math.isfinite(spread)
    assert spread > 0.0


def test_geom_stats_are_pure_functions() -> None:
    record = json.loads(MING_RECORD.read_text(encoding="utf-8"))
    baseline = deepcopy(record)

    first = (glyph_centroid(record), centroid_distance(record), inertia_spread(record))
    second = (glyph_centroid(record), centroid_distance(record), inertia_spread(record))

    assert first == second
    assert record == baseline
