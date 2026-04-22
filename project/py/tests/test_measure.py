from pathlib import Path

import pytest

from olik_font.geom import apply_affine_to_point
from olik_font.prototypes.measure import (
    CANONICAL,
    measure_bbox_from_strokes,
    measure_instance_transform,
)
from olik_font.sources.makemeahanzi import load_mmh_graphics

ROOT = Path(__file__).resolve().parents[1]
MMH = ROOT / "data" / "mmh" / "graphics.txt"

pytestmark = pytest.mark.skipif(not MMH.exists(), reason="run Plan 01 Task 4 first")


def test_measure_bbox_from_ming_sun_strokes_is_squareish():
    ming = load_mmh_graphics(MMH)["明"]

    bbox = measure_bbox_from_strokes([ming.strokes[i] for i in (0, 1, 2, 3)])
    width = bbox[2] - bbox[0]
    height = bbox[3] - bbox[1]

    assert bbox != CANONICAL
    assert width / height == pytest.approx(0.596431480908287, rel=0.05)
    assert 0.5 <= width / height <= 1.6


def test_measure_instance_transform_uses_measured_ming_moon_bbox():
    ming = load_mmh_graphics(MMH)["明"]
    sun_bbox = measure_bbox_from_strokes([ming.strokes[i] for i in (0, 1, 2, 3)])
    moon_paths = [ming.strokes[i] for i in (4, 5, 6, 7)]
    moon_bbox = measure_bbox_from_strokes(moon_paths)

    assert (sun_bbox[0] + sun_bbox[2]) / 2.0 < (moon_bbox[0] + moon_bbox[2]) / 2.0
    assert (moon_bbox[3] - moon_bbox[1]) > (moon_bbox[2] - moon_bbox[0])

    transform = measure_instance_transform(moon_paths)

    assert apply_affine_to_point(transform, (0.0, 0.0)) == pytest.approx(
        (moon_bbox[0], moon_bbox[1])
    )
    assert apply_affine_to_point(transform, (1024.0, 1024.0)) == pytest.approx(
        (moon_bbox[2], moon_bbox[3])
    )
