"""variant_match.match_in_slot — Hungarian bbox-IoU pairing of a canonical
component's strokes (transformed into a context char's measured slot)
against the context char's own strokes."""

from __future__ import annotations

from olik_font.bulk.variant_match import MatchResult, match_in_slot

# Canonical 0..1024 y-up space.
CANONICAL_SLOT = (0.0, 0.0, 1024.0, 1024.0)


def _rect_path(x0: float, y0: float, x1: float, y1: float) -> str:
    """Closed axis-aligned rectangle path-d (clockwise)."""
    return f"M{x0},{y0} L{x1},{y0} L{x1},{y1} L{x0},{y1} Z"


def test_identity_match_scores_near_one() -> None:
    """Canonical and context have identical strokes in identical positions;
    slot is the full canonical bbox → every pair's IoU ≈ 1.0."""
    canonical = [_rect_path(0, 0, 256, 256), _rect_path(512, 512, 1024, 1024)]
    context = [_rect_path(0, 0, 256, 256), _rect_path(512, 512, 1024, 1024)]
    result = match_in_slot(canonical, context, CANONICAL_SLOT)
    assert isinstance(result, MatchResult)
    assert result.k_gt_m is False
    assert result.below_floor is False
    assert result.mean_iou > 0.99
    assert result.min_iou > 0.99
    # Pairs are {(0,0), (1,1)} regardless of order.
    pair_set = {(p.canonical_idx, p.context_idx) for p in result.pairs}
    assert pair_set == {(0, 0), (1, 1)}


def test_context_order_permutation_does_not_break_pairing() -> None:
    """Hungarian must find the correct assignment even when context
    strokes are shuffled relative to canonical order."""
    canonical = [_rect_path(0, 0, 100, 100), _rect_path(900, 900, 1024, 1024)]
    # Context same shapes but reversed.
    context = [_rect_path(900, 900, 1024, 1024), _rect_path(0, 0, 100, 100)]
    result = match_in_slot(canonical, context, CANONICAL_SLOT)
    assert result.k_gt_m is False
    assert result.below_floor is False
    assert result.mean_iou > 0.99
    by_canonical = {p.canonical_idx: p.context_idx for p in result.pairs}
    assert by_canonical[0] == 1
    assert by_canonical[1] == 0


def test_slot_transform_repositions_canonical_into_slot_frame() -> None:
    """Canonical occupies the full canonical bbox (0..1024); slot is the
    upper half of a 1024x1024 glyph (y-up: HIGH y).
    After transform, canonical's strokes live in y=[512..1024]; context
    strokes also in y=[512..1024] → match."""
    canonical = [_rect_path(0, 0, 1024, 1024)]
    context = [_rect_path(0, 512, 1024, 1024)]
    slot = (0.0, 512.0, 1024.0, 1024.0)
    result = match_in_slot(canonical, context, slot)
    assert result.k_gt_m is False
    assert result.mean_iou > 0.99


def test_k_gt_m_when_canonical_has_more_strokes_than_context() -> None:
    """Canonical: 3 strokes; context: 2 strokes. No valid 1:1 assignment.
    Return MatchResult(k_gt_m=True) immediately."""
    canonical = [
        _rect_path(0, 0, 100, 100),
        _rect_path(200, 200, 300, 300),
        _rect_path(400, 400, 500, 500),
    ]
    context = [
        _rect_path(0, 0, 100, 100),
        _rect_path(200, 200, 300, 300),
    ]
    result = match_in_slot(canonical, context, CANONICAL_SLOT)
    assert result.k_gt_m is True
    assert result.pairs == ()
    assert result.mean_iou == 0.0


def test_below_floor_flag_when_any_pair_under_threshold() -> None:
    """Canonical has 2 strokes; context has 2 strokes but one is wildly
    displaced so Hungarian is forced to pair it with a canonical stroke
    at IoU < floor."""
    canonical = [_rect_path(0, 0, 100, 100), _rect_path(200, 200, 300, 300)]
    context = [
        _rect_path(0, 0, 100, 100),  # pairs with canonical[0] at ~1.0
        _rect_path(900, 900, 1024, 1024),  # no overlap with canonical[1]
    ]
    result = match_in_slot(canonical, context, CANONICAL_SLOT, per_stroke_floor=0.30)
    assert result.k_gt_m is False
    assert result.below_floor is True
    # Still returns pairs for introspection — caller decides what to do.
    assert len(result.pairs) == 2


def test_extra_context_strokes_are_unused() -> None:
    """Canonical: 2 strokes; context: 4 strokes. Hungarian picks best 2
    context strokes to pair with; the other 2 are ignored."""
    canonical = [_rect_path(0, 0, 100, 100), _rect_path(900, 900, 1024, 1024)]
    context = [
        _rect_path(0, 0, 100, 100),  # matches canonical[0]
        _rect_path(500, 500, 600, 600),  # distractor
        _rect_path(450, 450, 550, 550),  # distractor
        _rect_path(900, 900, 1024, 1024),  # matches canonical[1]
    ]
    result = match_in_slot(canonical, context, CANONICAL_SLOT)
    assert result.k_gt_m is False
    assert result.below_floor is False
    assert result.mean_iou > 0.99
    matched_context = {p.context_idx for p in result.pairs}
    assert matched_context == {0, 3}


def test_empty_canonical_returns_trivially_passing_match() -> None:
    """Edge case: zero canonical strokes. Can't happen in practice
    (components always have strokes), but the matcher should not crash."""
    result = match_in_slot([], [_rect_path(0, 0, 100, 100)], CANONICAL_SLOT)
    assert result.k_gt_m is False
    assert result.below_floor is False
    assert result.pairs == ()
    assert result.mean_iou == 1.0  # vacuously perfect


def test_empty_context_with_nonempty_canonical_is_k_gt_m() -> None:
    result = match_in_slot([_rect_path(0, 0, 100, 100)], [], CANONICAL_SLOT)
    assert result.k_gt_m is True
    assert result.pairs == ()
    assert result.mean_iou == 0.0
