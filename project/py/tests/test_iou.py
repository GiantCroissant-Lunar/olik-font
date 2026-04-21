from olik_font.compose.iou import bbox_iou, iou_report_for


def test_identical_bboxes_are_1():
    a = (0.0, 0.0, 10.0, 10.0)
    assert abs(bbox_iou(a, a) - 1.0) < 1e-9


def test_disjoint_bboxes_are_0():
    assert bbox_iou((0, 0, 1, 1), (10, 10, 11, 11)) == 0.0


def test_half_overlap():
    # two 10x10 boxes offset by 5 in x
    a = (0.0, 0.0, 10.0, 10.0)
    b = (5.0, 0.0, 15.0, 10.0)
    # intersection = 5x10 = 50; union = 10x10 + 10x10 - 50 = 150
    assert abs(bbox_iou(a, b) - 50 / 150) < 1e-9


def test_iou_report_from_bboxes():
    composed = [(0, 0, 10, 10), (20, 0, 30, 10)]
    mmh = [(0, 0, 10, 10), (22, 0, 32, 10)]
    report = iou_report_for(composed, mmh)
    assert report["mean"] > 0.6
    assert report["min"] < report["mean"]
    assert "per_stroke" in report
