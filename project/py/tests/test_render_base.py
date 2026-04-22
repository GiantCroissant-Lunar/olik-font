from __future__ import annotations

from collections import deque
from pathlib import Path

from PIL import Image

from olik_font.styling.render_base import render_base_png


def test_render_base_png_rasterizes_two_horizontal_strokes(tmp_path: Path):
    record = {
        "glyph_id": "二",
        "coord_space": {"width": 1024, "height": 1024},
        "stroke_instances": [
            {
                "id": "s0",
                "path": "M 128 256 L 896 256",
                "median": [[128, 256], [896, 256]],
            },
            {
                "id": "s1",
                "path": "M 128 768 L 896 768",
                "median": [[128, 768], [896, 768]],
            },
        ],
    }
    dest = tmp_path / "base.png"

    result = render_base_png(record, dest, size=256)

    assert result == dest
    assert dest.exists()

    image = Image.open(dest).convert("L")
    boxes = sorted(_ink_component_boxes(image), key=lambda box: box[1])

    assert len(boxes) == 2

    top, bottom = boxes
    assert top[0] == 32
    assert top[2] == 224
    assert 58 <= top[1] <= 70
    assert 58 <= top[3] <= 70

    assert bottom[0] == 32
    assert bottom[2] == 224
    assert 186 <= bottom[1] <= 198
    assert 186 <= bottom[3] <= 198


def _ink_component_boxes(image: Image.Image) -> list[tuple[int, int, int, int]]:
    width, height = image.size
    pixels = image.load()
    seen: set[tuple[int, int]] = set()
    boxes: list[tuple[int, int, int, int]] = []

    for y in range(height):
        for x in range(width):
            if pixels[x, y] >= 250 or (x, y) in seen:
                continue
            boxes.append(_component_box(pixels, width, height, x, y, seen))
    return boxes


def _component_box(
    pixels,
    width: int,
    height: int,
    start_x: int,
    start_y: int,
    seen: set[tuple[int, int]],
) -> tuple[int, int, int, int]:
    q: deque[tuple[int, int]] = deque([(start_x, start_y)])
    seen.add((start_x, start_y))
    min_x = max_x = start_x
    min_y = max_y = start_y

    while q:
        x, y = q.popleft()
        min_x = min(min_x, x)
        max_x = max(max_x, x)
        min_y = min(min_y, y)
        max_y = max(max_y, y)
        for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
            if nx < 0 or ny < 0 or nx >= width or ny >= height:
                continue
            if pixels[nx, ny] >= 250 or (nx, ny) in seen:
                continue
            seen.add((nx, ny))
            q.append((nx, ny))

    return (min_x, min_y, max_x, max_y)
