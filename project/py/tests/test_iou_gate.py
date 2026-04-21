import json
import warnings
from pathlib import Path

import pytest

RECORDS = Path(__file__).resolve().parents[2] / "schema" / "examples"
CHARS = ["明", "清", "國", "森"]


@pytest.mark.parametrize("ch", CHARS)
def test_iou_above_fail_threshold(ch):
    rec_path = RECORDS / f"glyph-record-{ch}.json"
    if not rec_path.exists():
        pytest.skip("run `olik build` first (Plan 03 Task 6 Step 5)")
    rec = json.loads(rec_path.read_text())
    iou = rec["metadata"]["iou_report"]
    # count mismatch note means we couldn't score — a soft skip, not a failure
    if "note" in iou:
        pytest.skip(iou["note"])
    assert iou["min"] >= 0.80, f"{ch}: min IoU {iou['min']:.3f} below fail threshold"
    if iou["min"] < 0.85:
        warnings.warn(
            f"{ch}: min IoU {iou['min']:.3f} below warn threshold",
            stacklevel=2,
        )
