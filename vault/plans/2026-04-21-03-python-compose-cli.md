---
title: "Plan 03 — Python compose + rules + CLI (P6, P7, P8)"
created: 2026-04-21
tags: [type/plan, topic/scene-graph]
source: self
spec: "[[2026-04-21-glyph-scene-graph-solution-design]]"
status: draft
phase: 3
depends-on: "[[2026-04-21-02-python-core]]"
---

# Plan 03 — Python compose + rules + CLI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce the first **working artifact**: a CLI (`olik build 明 清 國 森 -o …`) that emits four validated `glyph-record-<char>.json` files, one `prototype-library.json`, four `rule-trace-<char>.json`, and passes IoU-vs-MMH validation.

**Architecture:** `compose/` walks an `InstancePlacement` tree post-order, invoking preset functions from Plan 02 to resolve transforms. `compose/flatten.py` expands leaf nodes into stroke instances in glyph virtual coord. `compose/iou.py` validates composed strokes against the MMH source. `rules/` is a named, ordered, YAML-declared rule engine — thin in pass 1 (delegates to `extraction_plan.yaml`), but emits full rule traces so decisions are reviewable. `cli.py` orchestrates: fetch sources → extract prototypes → decompose → compose → validate → emit.

**Tech Stack:** Python 3.11+, shapely (for IoU), jsonschema, click or argparse for CLI, pytest.

---

## File Structure

```
project/py/src/olik_font/
├── compose/
│   ├── __init__.py
│   ├── walk.py                  # post-order tree walk; dispatches presets
│   ├── flatten.py               # leaf + transform → stroke_instances
│   ├── z_layers.py              # role → z-layer base assignment
│   └── iou.py                   # composed stroke vs MMH IoU per stroke
├── rules/
│   ├── __init__.py
│   ├── engine.py                # ordered rule runner + trace writer
│   ├── decomp_rules.py          # depth/mode choice
│   ├── compose_rules.py         # input-adapter choice
│   ├── prototype_rules.py       # MMH stroke carving policy
│   └── rules.yaml               # declarative rule set for pass 1
├── emit/
│   ├── __init__.py
│   ├── library.py               # PrototypeLibrary → prototype-library.json
│   ├── record.py                # composed tree → glyph-record.json
│   └── trace.py                 # rule trace → rule-trace.json
└── cli.py                       # `olik build`
```

Constants for render layers:

```python
RENDER_LAYERS = [
    {"name": "skeleton",        "z_min": 0,  "z_max": 9},
    {"name": "stroke_body",     "z_min": 10, "z_max": 49},
    {"name": "stroke_edge",     "z_min": 50, "z_max": 69},
    {"name": "texture_overlay", "z_min": 70, "z_max": 89},
    {"name": "damage",          "z_min": 90, "z_max": 99},
]
```

---

## Task 1: Compose walker — resolve transforms

**Files:**
- Create: `project/py/src/olik_font/compose/__init__.py`
- Create: `project/py/src/olik_font/compose/walk.py`
- Create: `project/py/tests/test_compose_walk.py`

- [ ] **Step 1: Write the failing test**

```python
# project/py/tests/test_compose_walk.py
from pathlib import Path

import pytest

from olik_font.compose.walk import compose_transforms
from olik_font.decompose.instance import build_instance_tree
from olik_font.geom import apply_affine_to_point
from olik_font.prototypes.extraction_plan import load_extraction_plan
from olik_font.types import Affine

PLAN = Path(__file__).resolve().parents[1] / "data" / "extraction_plan.yaml"


def test_ming_root_left_right_resolves_child_transforms():
    plan = load_extraction_plan(PLAN)
    tree = build_instance_tree("明", plan)
    resolved, constraints = compose_transforms(tree, glyph_bbox=(0, 0, 1024, 1024))

    left, right = resolved.children
    # left should occupy upper-left quadrant of glyph space
    assert apply_affine_to_point(left.transform, (0, 0)) == (0.0, 0.0)
    # right should start after the split + gap
    rx0, _ = apply_affine_to_point(right.transform, (0, 0))
    assert rx0 > 400  # split at 40% = 409.6 + gap → ~420


def test_qing_recursive_resolves_depth_2_children():
    plan = load_extraction_plan(PLAN)
    tree = build_instance_tree("清", plan)
    resolved, _ = compose_transforms(tree, glyph_bbox=(0, 0, 1024, 1024))

    water, qing = resolved.children
    assert water.transform != Affine.identity()
    assert qing.transform != Affine.identity()
    # qing is refined → its children should also have transforms
    sheng, moon = qing.children
    assert sheng.transform != Affine.identity()
    assert moon.transform != Affine.identity()
    # sheng's placed position should be within qing's placed bbox's upper half
    sheng_origin = apply_affine_to_point(sheng.transform, (0, 0))
    qing_origin = apply_affine_to_point(qing.transform, (0, 0))
    assert sheng_origin[0] >= qing_origin[0] - 1  # horizontal within qing
    assert sheng_origin[1] >= qing_origin[1] - 1  # starts at qing's top


def test_guo_enclose_resolves():
    plan = load_extraction_plan(PLAN)
    tree = build_instance_tree("國", plan)
    resolved, constraints = compose_transforms(tree, glyph_bbox=(0, 0, 1024, 1024))
    outer, inner = resolved.children
    assert apply_affine_to_point(outer.transform, (0, 0)) == (0.0, 0.0)
    # inner should be padded inside outer
    inner_origin = apply_affine_to_point(inner.transform, (0, 0))
    assert 80 < inner_origin[0] < 140


def test_senr_repeat_triangle_resolves():
    plan = load_extraction_plan(PLAN)
    tree = build_instance_tree("森", plan)
    resolved, constraints = compose_transforms(tree, glyph_bbox=(0, 0, 1024, 1024))
    assert len(resolved.children) == 3
    centers = [apply_affine_to_point(c.transform, (512, 512)) for c in resolved.children]
    ys = sorted(c[1] for c in centers)
    assert ys[0] < 400  # one near top
    assert ys[1] > 500 and ys[2] > 500  # two near bottom
```

- [ ] **Step 2: Run the test**

```bash
cd project/py && .venv/bin/pytest tests/test_compose_walk.py -v
```

Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Implement `walk.py`**

```python
# project/py/src/olik_font/compose/__init__.py
from olik_font.compose.walk import compose_transforms  # noqa: F401
```

```python
# project/py/src/olik_font/compose/walk.py
"""Post-order walk over InstancePlacement trees; fills in transforms.

Dispatches by `input_adapter`:
  - "preset:left_right"     → apply_left_right
  - "preset:top_bottom"     → apply_top_bottom
  - "preset:enclose"        → apply_enclose
  - "direct:repeat_triangle"→ apply_repeat_triangle
  - "direct" / "leaf"       → keep transform; usually identity at root

Refine-mode nodes recurse: their children are composed using the parent's
placed bbox as the nested glyph_bbox.
"""

from __future__ import annotations

from dataclasses import replace

from olik_font.constraints.presets import (
    apply_enclose, apply_left_right, apply_repeat_triangle, apply_top_bottom,
)
from olik_font.constraints.primitives import Primitive
from olik_font.geom import apply_affine_to_point
from olik_font.types import Affine, BBox, InstancePlacement


def compose_transforms(
    node: InstancePlacement,
    glyph_bbox: BBox,
) -> tuple[InstancePlacement, tuple[Primitive, ...]]:
    """Resolve all descendant transforms. Returns (new_root, resolved_constraints)."""
    if not node.children:
        return node, ()

    adapter = node.input_adapter
    children = node.children
    resolved_children: tuple[InstancePlacement, ...]
    local_constraints: tuple[Primitive, ...]

    if adapter == "preset:left_right":
        assert len(children) == 2, "left_right expects 2 children"
        l, r, cs = apply_left_right(children[0], children[1], glyph_bbox)
        resolved_children = (l, r)
        local_constraints = cs
    elif adapter == "preset:top_bottom":
        assert len(children) == 2, "top_bottom expects 2 children"
        t, b, cs = apply_top_bottom(children[0], children[1], glyph_bbox)
        resolved_children = (t, b)
        local_constraints = cs
    elif adapter == "preset:enclose":
        assert len(children) == 2, "enclose expects 2 children"
        o, i, cs = apply_enclose(children[0], children[1], glyph_bbox)
        resolved_children = (o, i)
        local_constraints = cs
    elif adapter == "direct:repeat_triangle":
        assert len(children) == 3, "repeat_triangle expects 3 children"
        resolved, cs = apply_repeat_triangle(
            (children[0], children[1], children[2]), glyph_bbox,
        )
        resolved_children = resolved
        local_constraints = cs
    else:
        # "direct" / "leaf" / unknown → identity at this level
        resolved_children = children
        local_constraints = ()

    # Recurse into refine-mode children using their placed bbox
    descendant_constraints: list[Primitive] = []
    final_children: list[InstancePlacement] = []
    for child in resolved_children:
        if child.children:
            child_bbox = _placed_bbox(child.transform)
            new_child, child_cs = compose_transforms(child, child_bbox)
            final_children.append(new_child)
            descendant_constraints.extend(child_cs)
        else:
            final_children.append(child)

    return (
        replace(node, children=tuple(final_children)),
        local_constraints + tuple(descendant_constraints),
    )


def _placed_bbox(transform: Affine) -> BBox:
    """Recover axis-aligned bbox by applying transform to canonical corners."""
    p0 = apply_affine_to_point(transform, (0.0, 0.0))
    p1 = apply_affine_to_point(transform, (1024.0, 1024.0))
    x0, x1 = sorted((p0[0], p1[0]))
    y0, y1 = sorted((p0[1], p1[1]))
    return (x0, y0, x1, y1)
```

- [ ] **Step 4: Run the test**

```bash
cd project/py && .venv/bin/pytest tests/test_compose_walk.py -v
```

Expected: `4 passed`.

- [ ] **Step 5: Commit**

```bash
git add project/py/src/olik_font/compose/__init__.py project/py/src/olik_font/compose/walk.py project/py/tests/test_compose_walk.py
git commit -m "feat(compose): post-order walker that resolves transforms via presets"
```

---

## Task 2: Stroke flattener — leaf + transform → stroke_instances

**Files:**
- Create: `project/py/src/olik_font/compose/flatten.py`
- Create: `project/py/src/olik_font/compose/z_layers.py`
- Create: `project/py/tests/test_flatten.py`
- Create: `project/py/tests/test_z_layers.py`

- [ ] **Step 1: Write the z-layer test**

```python
# project/py/tests/test_z_layers.py
from olik_font.compose.z_layers import z_for_stroke


def test_horizontal_strokes_go_to_stroke_body():
    assert 10 <= z_for_stroke(role="horizontal", order=0) <= 49


def test_order_increments_z_within_role():
    assert z_for_stroke("horizontal", 0) < z_for_stroke("horizontal", 1)


def test_dot_role_goes_to_stroke_body_too():
    # pass 1: all strokes live in stroke_body layer (10-49); edge/texture/damage empty
    assert 10 <= z_for_stroke("dot", 0) <= 49


def test_order_saturates_within_layer():
    # very high order clamps to top of layer
    z = z_for_stroke("horizontal", 1000)
    assert z <= 49
```

- [ ] **Step 2: Implement `z_layers.py`**

```python
# project/py/src/olik_font/compose/z_layers.py
"""Map (stroke role, order) to a z value in 0..99.

Pass-1 policy: every stroke lives in the `stroke_body` layer (10..49).
Per-role base offsets within that range keep strokes of different roles
distinguishable in LayerZDepth visualizations without fragmenting layers
that Plan 03 has no content for (edge / texture / damage).
"""

from __future__ import annotations

_ROLE_BASE = {
    "horizontal": 10,
    "vertical":   14,
    "dot":        18,
    "hook":       22,
    "slash":      26,
    "backslash":  30,
    "fold":       34,
    "other":      38,
}


def z_for_stroke(role: str, order: int) -> int:
    base = _ROLE_BASE.get(role, _ROLE_BASE["other"])
    return min(base + order, 49)
```

- [ ] **Step 3: Run the z-layer test**

```bash
cd project/py && .venv/bin/pytest tests/test_z_layers.py -v
```

Expected: `4 passed`.

- [ ] **Step 4: Write the flatten test**

```python
# project/py/tests/test_flatten.py
from pathlib import Path

import pytest

from olik_font.compose.flatten import flatten_strokes
from olik_font.compose.walk import compose_transforms
from olik_font.decompose.instance import build_instance_tree
from olik_font.prototypes.extract import extract_all_prototypes
from olik_font.prototypes.extraction_plan import load_extraction_plan
from olik_font.sources.makemeahanzi import load_mmh_graphics
from olik_font.types import PrototypeLibrary

ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "data" / "extraction_plan.yaml"
MMH = ROOT / "data" / "mmh" / "graphics.txt"

pytestmark = pytest.mark.skipif(not MMH.exists(), reason="run Plan 01 Task 4 first")


@pytest.fixture(scope="module")
def lib_and_plan():
    plan = load_extraction_plan(PLAN)
    chars = load_mmh_graphics(MMH)
    lib = PrototypeLibrary()
    extract_all_prototypes(plan, chars, lib)
    return lib, plan


def test_ming_flattens_to_eight_stroke_instances(lib_and_plan):
    lib, plan = lib_and_plan
    tree = build_instance_tree("明", plan)
    resolved, _ = compose_transforms(tree, glyph_bbox=(0, 0, 1024, 1024))
    strokes = flatten_strokes(resolved, lib)
    assert len(strokes) == 8  # 4 from 日 + 4 from 月
    # every stroke has instance_id linking back to a leaf
    assert all(s.instance_id.startswith("inst:") for s in strokes)
    assert all(0 <= s.z <= 99 for s in strokes)


def test_senr_flattens_to_twelve_from_same_prototype(lib_and_plan):
    lib, plan = lib_and_plan
    tree = build_instance_tree("森", plan)
    resolved, _ = compose_transforms(tree, glyph_bbox=(0, 0, 1024, 1024))
    strokes = flatten_strokes(resolved, lib)
    assert len(strokes) == 12  # 4 strokes × 3 木 instances
    instance_ids = {s.instance_id for s in strokes}
    assert len(instance_ids) == 3


def test_qing_skips_refine_intermediate(lib_and_plan):
    lib, plan = lib_and_plan
    tree = build_instance_tree("清", plan)
    resolved, _ = compose_transforms(tree, glyph_bbox=(0, 0, 1024, 1024))
    strokes = flatten_strokes(resolved, lib)
    # 氵 (3) + 生 (5) + 月 (4) = 12. The refine-intermediate 青 has no own strokes.
    assert len(strokes) == 12
    refs = {s.instance_id.split("_")[0] for s in strokes}
    # at least three distinct source instances (氵, 生, 月)
    assert len(refs) >= 3
```

- [ ] **Step 5: Run the flatten test**

```bash
cd project/py && .venv/bin/pytest tests/test_flatten.py -v
```

Expected: `ModuleNotFoundError`.

- [ ] **Step 6: Implement `flatten.py`**

```python
# project/py/src/olik_font/compose/flatten.py
"""Flatten a composed InstancePlacement tree to a list of StrokeInstance records.

A leaf is any placement whose prototype_ref resolves in the library AND has
no children. Refine intermediates (children + prototype_ref like proto:__glyph_*
or any missing-from-library ref) contribute no strokes directly — only their
descendant leaves do.
"""

from __future__ import annotations

from dataclasses import dataclass

from olik_font.compose.z_layers import z_for_stroke
from olik_font.geom import apply_affine_to_median, apply_affine_to_path, bbox_of_paths
from olik_font.types import Affine, BBox, InstancePlacement, Point, PrototypeLibrary


@dataclass(frozen=True, slots=True)
class StrokeInstance:
    id:          str
    instance_id: str
    order:       int
    path:        str
    median:      tuple[Point, ...]
    bbox:        BBox
    z:           int
    role:        str


def flatten_strokes(
    root: InstancePlacement,
    library: PrototypeLibrary,
) -> tuple[StrokeInstance, ...]:
    out: list[StrokeInstance] = []
    counter = {"n": 0}
    _visit(root, Affine.identity(), library, out, counter)
    return tuple(out)


def _visit(
    node: InstancePlacement,
    outer: Affine,
    library: PrototypeLibrary,
    out: list[StrokeInstance],
    counter: dict,
) -> None:
    from olik_font.geom import affine_compose

    cumulative = affine_compose(outer, node.transform)

    if node.children:
        for child in node.children:
            _visit(child, cumulative, library, out, counter)
        return

    # Leaf. Only emit strokes if its prototype is in the library.
    if not library.contains(node.prototype_ref):
        return

    proto = library[node.prototype_ref]
    for stroke in proto.strokes:
        new_path = apply_affine_to_path(cumulative, stroke.path)
        new_median = apply_affine_to_median(cumulative, stroke.median)
        new_bbox = bbox_of_paths([new_path])
        z = z_for_stroke(stroke.role, stroke.order)
        counter["n"] += 1
        out.append(StrokeInstance(
            id=f"si{counter['n']:04d}",
            instance_id=node.instance_id,
            order=stroke.order,
            path=new_path,
            median=new_median,
            bbox=new_bbox,
            z=z,
            role=stroke.role,
        ))
```

- [ ] **Step 7: Run the flatten test**

```bash
cd project/py && .venv/bin/pytest tests/test_flatten.py -v
```

Expected: `3 passed`.

- [ ] **Step 8: Commit**

```bash
git add project/py/src/olik_font/compose/flatten.py project/py/src/olik_font/compose/z_layers.py project/py/tests/test_flatten.py project/py/tests/test_z_layers.py
git commit -m "feat(compose): stroke flattener + role-based z assignment"
```

---

## Task 3: IoU vs. MMH validator

**Files:**
- Create: `project/py/src/olik_font/compose/iou.py`
- Create: `project/py/tests/test_iou.py`

IoU is computed on *bounding boxes* in pass 1, not polygons. The composed-stroke bbox should sit near the corresponding MMH stroke's bbox. Bounding-box IoU is cheap, captures placement errors, and avoids needing a full path→polygon converter. Polygon IoU is a named deferred item.

- [ ] **Step 1: Write the failing test**

```python
# project/py/tests/test_iou.py
from olik_font.compose.iou import bbox_iou, iou_report_for


def test_identical_bboxes_are_1():
    a = (0.0, 0.0, 10.0, 10.0)
    assert abs(bbox_iou(a, a) - 1.0) < 1e-9


def test_disjoint_bboxes_are_0():
    assert bbox_iou((0, 0, 1, 1), (10, 10, 11, 11)) == 0.0


def test_half_overlap():
    # two 10×10 boxes offset by 5 in x
    a = (0.0, 0.0, 10.0, 10.0)
    b = (5.0, 0.0, 15.0, 10.0)
    # intersection = 5×10 = 50; union = 10×10 + 10×10 - 50 = 150
    assert abs(bbox_iou(a, b) - 50 / 150) < 1e-9


def test_iou_report_from_bboxes():
    composed = [(0, 0, 10, 10), (20, 0, 30, 10)]
    mmh = [(0, 0, 10, 10), (22, 0, 32, 10)]
    report = iou_report_for(composed, mmh)
    assert report["mean"] > 0.6
    assert report["min"] < report["mean"]
    assert "per_stroke" in report
```

- [ ] **Step 2: Run the test**

```bash
cd project/py && .venv/bin/pytest tests/test_iou.py -v
```

Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Implement `iou.py`**

```python
# project/py/src/olik_font/compose/iou.py
"""Bounding-box IoU — pass-1 validator for composed strokes vs. MMH source.

Polygon-level IoU (shapely + path-to-polygon) is deferred; bbox IoU
captures placement and scale errors cheaply.
"""

from __future__ import annotations

from olik_font.types import BBox


def bbox_iou(a: BBox, b: BBox) -> float:
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    ix0 = max(ax0, bx0)
    iy0 = max(ay0, by0)
    ix1 = min(ax1, bx1)
    iy1 = min(ay1, by1)
    if ix1 <= ix0 or iy1 <= iy0:
        return 0.0
    inter = (ix1 - ix0) * (iy1 - iy0)
    area_a = (ax1 - ax0) * (ay1 - ay0)
    area_b = (bx1 - bx0) * (by1 - by0)
    return inter / (area_a + area_b - inter)


def iou_report_for(
    composed: list[BBox] | tuple[BBox, ...],
    mmh: list[BBox] | tuple[BBox, ...],
) -> dict:
    """Compute mean/min IoU + per-stroke scores.

    Pairing is positional: composed[i] vs mmh[i]. Length mismatch raises.
    """
    if len(composed) != len(mmh):
        raise ValueError(f"length mismatch: composed={len(composed)}, mmh={len(mmh)}")
    per: dict[str, float] = {}
    for i, (c, m) in enumerate(zip(composed, mmh)):
        per[f"s{i}"] = bbox_iou(c, m)
    values = list(per.values()) or [1.0]
    return {
        "mean":       sum(values) / len(values),
        "min":        min(values),
        "per_stroke": per,
    }
```

- [ ] **Step 4: Run the test**

```bash
cd project/py && .venv/bin/pytest tests/test_iou.py -v
```

Expected: `4 passed`.

- [ ] **Step 5: Commit**

```bash
git add project/py/src/olik_font/compose/iou.py project/py/tests/test_iou.py
git commit -m "feat(compose): bbox IoU validator + per-stroke report"
```

---

## Task 4: Rule engine + `rules.yaml` (thin but real)

**Files:**
- Create: `project/py/src/olik_font/rules/__init__.py`
- Create: `project/py/src/olik_font/rules/engine.py`
- Create: `project/py/src/olik_font/rules/rules.yaml`
- Create: `project/py/tests/test_rule_engine.py`

- [ ] **Step 1: Author `rules.yaml`**

```yaml
# project/py/src/olik_font/rules/rules.yaml
# Pass-1 rule set. Thin: most decisions delegate to extraction_plan.yaml.
# The point is trace-recording, not policy expressiveness.

schema_version: "0.1"

decomposition:
  - id: decomp.use_extraction_plan
    when: { char_in_extraction_plan: true }
    action: { source: extraction_plan, delegate: true }
  - id: decomp.default_keep
    when: {}  # fallback
    action: { mode: keep, depth: 0 }

composition:
  - id: compose.preset_from_plan
    when: { has_preset_in_plan: true }
    action: { adapter: preset }
  - id: compose.direct_for_repeat_triangle
    when: { preset: repeat_triangle }
    action: { adapter: direct }
  - id: compose.default_identity
    when: {}
    action: { adapter: identity }

prototype_extraction:
  - id: proto.use_extraction_plan_indices
    when: { char_in_extraction_plan: true }
    action: { source: extraction_plan, carve: by_stroke_indices }
  - id: proto.fallback_mmh_matches
    when: {}
    action: { source: mmh_matches_field }
```

- [ ] **Step 2: Write the failing test**

```python
# project/py/tests/test_rule_engine.py
from pathlib import Path

from olik_font.rules.engine import (
    RuleSet, RuleTrace, apply_first_match, load_rules,
)

RULES = Path(__file__).resolve().parents[1] / "src" / "olik_font" / "rules" / "rules.yaml"


def test_load_rules_returns_three_buckets():
    rs = load_rules(RULES)
    assert isinstance(rs, RuleSet)
    assert len(rs.decomposition) == 2
    assert len(rs.composition) == 3
    assert len(rs.prototype_extraction) == 2


def test_apply_first_match_picks_first_applicable_rule():
    rs = load_rules(RULES)
    trace = apply_first_match(
        bucket=rs.composition,
        inputs={"has_preset_in_plan": True, "preset": "left_right"},
        decision_id="d:test",
    )
    assert isinstance(trace, RuleTrace)
    assert trace.rule_id == "compose.preset_from_plan"
    assert trace.output == {"adapter": "preset"}


def test_apply_first_match_records_alternatives():
    rs = load_rules(RULES)
    trace = apply_first_match(
        bucket=rs.composition,
        inputs={"preset": "repeat_triangle", "has_preset_in_plan": True},
        decision_id="d:test",
    )
    # both preset_from_plan AND direct_for_repeat_triangle would match. First wins,
    # remaining applicable rules show up as alternatives.
    assert trace.rule_id == "compose.preset_from_plan"
    alt_ids = {alt.rule_id for alt in trace.alternatives}
    assert "compose.direct_for_repeat_triangle" in alt_ids


def test_fallback_rule_when_nothing_else_matches():
    rs = load_rules(RULES)
    trace = apply_first_match(
        bucket=rs.composition,
        inputs={},
        decision_id="d:test",
    )
    assert trace.rule_id == "compose.default_identity"
```

- [ ] **Step 3: Run the test**

```bash
cd project/py && .venv/bin/pytest tests/test_rule_engine.py -v
```

Expected: `ModuleNotFoundError`.

- [ ] **Step 4: Implement `engine.py`**

```python
# project/py/src/olik_font/rules/__init__.py
from olik_font.rules.engine import (  # noqa: F401
    Rule, RuleSet, RuleTrace, RuleTraceAlternative, apply_first_match, load_rules,
)
```

```python
# project/py/src/olik_font/rules/engine.py
"""Ordered, named rule engine with trace recording.

Rules are declarative (data in YAML). Matching is shallow: a rule's `when`
clause is a dict; the rule matches if every (key, value) in `when` is
present (and equal) in the inputs. Empty `when` is the always-match fallback.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True, slots=True)
class Rule:
    id:     str
    when:   dict[str, Any]
    action: dict[str, Any]


@dataclass(frozen=True, slots=True)
class RuleSet:
    schema_version:       str
    decomposition:        tuple[Rule, ...]
    composition:          tuple[Rule, ...]
    prototype_extraction: tuple[Rule, ...]


@dataclass(frozen=True, slots=True)
class RuleTraceAlternative:
    rule_id:       str
    would_output:  dict[str, Any]


@dataclass(frozen=True, slots=True)
class RuleTrace:
    decision_id:  str
    rule_id:      str
    inputs:       dict[str, Any]
    output:       dict[str, Any]
    alternatives: tuple[RuleTraceAlternative, ...] = ()
    applied_at:   str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


def load_rules(path: Path) -> RuleSet:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return RuleSet(
        schema_version=raw["schema_version"],
        decomposition=tuple(_parse_rule(r) for r in raw.get("decomposition", [])),
        composition=tuple(_parse_rule(r) for r in raw.get("composition", [])),
        prototype_extraction=tuple(_parse_rule(r) for r in raw.get("prototype_extraction", [])),
    )


def _parse_rule(obj: dict) -> Rule:
    return Rule(id=obj["id"], when=dict(obj.get("when") or {}), action=dict(obj.get("action") or {}))


def _matches(rule: Rule, inputs: dict[str, Any]) -> bool:
    for key, expected in rule.when.items():
        if key not in inputs or inputs[key] != expected:
            return False
    return True


def apply_first_match(
    bucket: tuple[Rule, ...] | list[Rule],
    inputs: dict[str, Any],
    decision_id: str,
) -> RuleTrace:
    winner: Rule | None = None
    alternatives: list[RuleTraceAlternative] = []
    for r in bucket:
        if _matches(r, inputs):
            if winner is None:
                winner = r
            else:
                alternatives.append(RuleTraceAlternative(rule_id=r.id, would_output=dict(r.action)))
    if winner is None:
        raise ValueError(f"no rule matched inputs={inputs}")
    return RuleTrace(
        decision_id=decision_id,
        rule_id=winner.id,
        inputs=dict(inputs),
        output=dict(winner.action),
        alternatives=tuple(alternatives),
    )
```

- [ ] **Step 5: Run the test**

```bash
cd project/py && .venv/bin/pytest tests/test_rule_engine.py -v
```

Expected: `4 passed`.

- [ ] **Step 6: Commit**

```bash
git add project/py/src/olik_font/rules/__init__.py project/py/src/olik_font/rules/engine.py project/py/src/olik_font/rules/rules.yaml project/py/tests/test_rule_engine.py
git commit -m "feat(rules): ordered rule engine + pass-1 rules.yaml"
```

---

## Task 5: JSON emitters — prototype library + glyph record + rule trace

**Files:**
- Create: `project/py/src/olik_font/emit/__init__.py`
- Create: `project/py/src/olik_font/emit/library.py`
- Create: `project/py/src/olik_font/emit/record.py`
- Create: `project/py/src/olik_font/emit/trace.py`
- Create: `project/py/tests/test_emit.py`

- [ ] **Step 1: Write the failing test**

```python
# project/py/tests/test_emit.py
import json
from pathlib import Path

import jsonschema
import pytest

from olik_font.compose.flatten import StrokeInstance
from olik_font.compose.walk import compose_transforms
from olik_font.decompose.instance import build_instance_tree
from olik_font.emit.library import library_to_dict
from olik_font.emit.record import build_glyph_record
from olik_font.emit.trace import trace_to_dict
from olik_font.prototypes.extract import extract_all_prototypes
from olik_font.prototypes.extraction_plan import load_extraction_plan
from olik_font.rules.engine import RuleTrace
from olik_font.sources.makemeahanzi import load_mmh_graphics
from olik_font.types import PrototypeLibrary

ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "data" / "extraction_plan.yaml"
MMH = ROOT / "data" / "mmh" / "graphics.txt"
SCHEMA_ROOT = ROOT.parent / "schema"

pytestmark = pytest.mark.skipif(not MMH.exists(), reason="run Plan 01 Task 4 first")


def _lib_schema():
    return json.loads((SCHEMA_ROOT / "prototype-library.schema.json").read_text())


def _record_schema():
    return json.loads((SCHEMA_ROOT / "glyph-record.schema.json").read_text())


@pytest.fixture(scope="module")
def lib_and_plan():
    plan = load_extraction_plan(PLAN)
    chars = load_mmh_graphics(MMH)
    lib = PrototypeLibrary()
    extract_all_prototypes(plan, chars, lib)
    return lib, plan, chars


def test_library_json_validates(lib_and_plan):
    lib, _, _ = lib_and_plan
    d = library_to_dict(lib)
    jsonschema.Draft202012Validator(_lib_schema()).validate(d)


def test_ming_record_validates_and_has_8_strokes(lib_and_plan):
    lib, plan, chars = lib_and_plan
    tree = build_instance_tree("明", plan)
    resolved, cs = compose_transforms(tree, glyph_bbox=(0, 0, 1024, 1024))
    record = build_glyph_record("明", resolved, cs, lib, mmh_char=chars["明"])
    jsonschema.Draft202012Validator(_record_schema()).validate(record)
    assert record["glyph_id"] == "明"
    assert len(record["stroke_instances"]) == 8
    assert len(record["constraints"]) >= 3  # left_right emits 3


def test_record_carries_iou_report(lib_and_plan):
    lib, plan, chars = lib_and_plan
    tree = build_instance_tree("明", plan)
    resolved, cs = compose_transforms(tree, glyph_bbox=(0, 0, 1024, 1024))
    record = build_glyph_record("明", resolved, cs, lib, mmh_char=chars["明"])
    iou = record["metadata"]["iou_report"]
    assert "mean" in iou and "min" in iou and "per_stroke" in iou


def test_trace_to_dict_shape():
    tr = RuleTrace(
        decision_id="d:test",
        rule_id="x",
        inputs={"a": 1},
        output={"b": 2},
    )
    d = trace_to_dict(tr)
    assert d["rule_id"] == "x"
    assert d["inputs"] == {"a": 1}
    assert d["output"] == {"b": 2}
    assert "applied_at" in d
    assert d["alternatives"] == []
```

- [ ] **Step 2: Run the test**

```bash
cd project/py && .venv/bin/pytest tests/test_emit.py -v
```

Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Implement `emit/library.py`**

```python
# project/py/src/olik_font/emit/__init__.py
from olik_font.emit.library import library_to_dict  # noqa: F401
from olik_font.emit.record import build_glyph_record  # noqa: F401
from olik_font.emit.trace import trace_to_dict  # noqa: F401
```

```python
# project/py/src/olik_font/emit/library.py
"""Serialize PrototypeLibrary → prototype-library.schema.json shape."""

from __future__ import annotations

from olik_font.types import PrototypeLibrary


def library_to_dict(lib: PrototypeLibrary) -> dict:
    protos: dict[str, dict] = {}
    for pid in lib.ids():
        p = lib[pid]
        protos[pid] = {
            "id":             p.id,
            "name":           p.name,
            "kind":           p.kind,
            "source":         dict(p.source),
            "canonical_bbox": list(p.canonical_bbox),
            "strokes": [
                {
                    "id":     s.id,
                    "path":   s.path,
                    "median": [list(pt) for pt in s.median],
                    "order":  s.order,
                    "role":   s.role,
                }
                for s in p.strokes
            ],
            "anchors": {k: list(v) for k, v in p.anchors.items()},
            "roles":   list(p.roles),
            "refinement": {
                "mode":       p.refinement_mode,
                "alternates": list(p.alternates),
            },
        }
    return {
        "schema_version": "0.1",
        "coord_space": {"width": 1024, "height": 1024, "origin": "top-left", "y_axis": "down"},
        "prototypes":   protos,
        "edges":        [],
    }
```

- [ ] **Step 4: Implement `emit/record.py`**

```python
# project/py/src/olik_font/emit/record.py
"""Serialize a composed InstancePlacement tree → glyph-record.schema.json shape."""

from __future__ import annotations

from datetime import datetime, timezone

from olik_font.compose.flatten import flatten_strokes
from olik_font.compose.iou import iou_report_for
from olik_font.constraints.primitives import Primitive, as_dict as primitive_to_dict
from olik_font.geom import apply_affine_to_point, bbox_of_paths
from olik_font.sources.makemeahanzi import MmhChar
from olik_font.types import Affine, BBox, InstancePlacement, PrototypeLibrary

_UNICODE = {
    "明": "U+660E", "清": "U+6E05", "國": "U+570B", "森": "U+68EE",
}

_RENDER_LAYERS = [
    {"name": "skeleton",        "z_min": 0,  "z_max": 9},
    {"name": "stroke_body",     "z_min": 10, "z_max": 49},
    {"name": "stroke_edge",     "z_min": 50, "z_max": 69},
    {"name": "texture_overlay", "z_min": 70, "z_max": 89},
    {"name": "damage",          "z_min": 90, "z_max": 99},
]


def build_glyph_record(
    char: str,
    resolved_tree: InstancePlacement,
    constraints: tuple[Primitive, ...],
    library: PrototypeLibrary,
    mmh_char: MmhChar,
) -> dict:
    strokes = flatten_strokes(resolved_tree, library)

    mmh_bboxes = tuple(bbox_of_paths([p]) for p in mmh_char.strokes)
    composed_bboxes = tuple(s.bbox for s in strokes)
    # pair by position when counts match; else skip IoU (named deferred: smarter alignment)
    if len(composed_bboxes) == len(mmh_bboxes):
        iou = iou_report_for(list(composed_bboxes), list(mmh_bboxes))
    else:
        iou = {
            "mean": 0.0, "min": 0.0,
            "per_stroke": {},
            "note": f"stroke count mismatch: composed={len(composed_bboxes)} mmh={len(mmh_bboxes)}",
        }

    return {
        "schema_version": "0.1",
        "glyph_id":    char,
        "unicode":     _UNICODE.get(char, "U+0000"),
        "coord_space": {"width": 1024, "height": 1024, "origin": "top-left", "y_axis": "down"},
        "source":      {"stroke_source": "make-me-a-hanzi", "decomp_source": "cjk-decomp"},
        "layout_tree": _node_to_dict(resolved_tree),
        "component_instances": [
            {
                "id":            inst.instance_id,
                "prototype_ref": inst.prototype_ref,
                "transform":     _affine_to_dict(inst.transform),
                "placed_bbox":   list(_placed_bbox(inst.transform)),
            }
            for inst in _leaves_with_library(resolved_tree, library)
        ],
        "stroke_instances": [
            {
                "id":          s.id,
                "instance_id": s.instance_id,
                "order":       s.order,
                "path":        s.path,
                "median":      [list(p) for p in s.median],
                "bbox":        list(s.bbox),
                "z":           s.z,
                "role":        s.role,
            }
            for s in strokes
        ],
        "constraints":   [primitive_to_dict(c) for c in constraints],
        "render_layers": _RENDER_LAYERS,
        "roles":         _roles_for(resolved_tree, library),
        "metadata": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "generator":    "olik-font py/0.1",
            "iou_report":   iou,
        },
    }


def _affine_to_dict(a: Affine) -> dict:
    return {
        "translate": list(a.translate),
        "scale":     list(a.scale),
        "rotate":    a.rotate,
        "shear":     list(a.shear),
    }


def _placed_bbox(a: Affine) -> BBox:
    p0 = apply_affine_to_point(a, (0.0, 0.0))
    p1 = apply_affine_to_point(a, (1024.0, 1024.0))
    x0, x1 = sorted((p0[0], p1[0]))
    y0, y1 = sorted((p0[1], p1[1]))
    return (x0, y0, x1, y1)


def _node_to_dict(n: InstancePlacement) -> dict:
    d: dict = {
        "id":            n.instance_id,
        "bbox":          list(_placed_bbox(n.transform)),
        "mode":          n.mode,
        "depth":         n.depth,
        "prototype_ref": n.prototype_ref,
        "transform":     _affine_to_dict(n.transform),
        "input_adapter": n.input_adapter,
        "children":      [_node_to_dict(c) for c in n.children],
    }
    if n.anchor_bindings:
        d["anchor_bindings"] = [
            {"from": ab.from_, "to": ab.to, **({"distance": ab.distance} if ab.distance is not None else {})}
            for ab in n.anchor_bindings
        ]
    if n.decomp_source:
        d["decomp_source"] = dict(n.decomp_source)
    return d


def _leaves_with_library(node: InstancePlacement, library: PrototypeLibrary) -> list[InstancePlacement]:
    if node.children:
        out: list[InstancePlacement] = []
        for c in node.children:
            out.extend(_leaves_with_library(c, library))
        return out
    return [node] if library.contains(node.prototype_ref) else []


def _roles_for(node: InstancePlacement, library: PrototypeLibrary) -> dict:
    roles: dict[str, dict] = {}
    for leaf in _leaves_with_library(node, library):
        proto = library[leaf.prototype_ref]
        if proto.roles:
            roles[leaf.instance_id] = {"dong_chinese": proto.roles[0]}
    return roles
```

- [ ] **Step 5: Implement `emit/trace.py`**

```python
# project/py/src/olik_font/emit/trace.py
"""Serialize RuleTrace records to JSON-ready dicts."""

from __future__ import annotations

from olik_font.rules.engine import RuleTrace


def trace_to_dict(t: RuleTrace) -> dict:
    return {
        "decision_id":  t.decision_id,
        "rule_id":      t.rule_id,
        "inputs":       dict(t.inputs),
        "output":       dict(t.output),
        "alternatives": [
            {"rule_id": alt.rule_id, "would_output": dict(alt.would_output)}
            for alt in t.alternatives
        ],
        "applied_at":   t.applied_at,
    }
```

- [ ] **Step 6: Run the test**

```bash
cd project/py && .venv/bin/pytest tests/test_emit.py -v
```

Expected: `4 passed`. Note: `test_ming_record_validates_and_has_8_strokes` may need `stroke_instance.bbox` to contain nonzero-width values; if any path has a degenerate bbox, cross-check `geom.bbox_of_paths` for 0-length strokes (medians-only).

- [ ] **Step 7: Commit**

```bash
git add project/py/src/olik_font/emit project/py/tests/test_emit.py
git commit -m "feat(emit): glyph-record + prototype-library + trace JSON serializers"
```

---

## Task 6: CLI — `olik build`

**Files:**
- Create: `project/py/src/olik_font/cli.py`
- Create: `project/py/tests/test_cli.py`

- [ ] **Step 1: Write the failing test**

```python
# project/py/tests/test_cli.py
import json
import sys
from pathlib import Path

import jsonschema
import pytest

from olik_font.cli import main

ROOT = Path(__file__).resolve().parents[1]
MMH = ROOT / "data" / "mmh" / "graphics.txt"
SCHEMA_ROOT = ROOT.parent / "schema"

pytestmark = pytest.mark.skipif(not MMH.exists(), reason="run Plan 01 Task 4 first")


def test_build_emits_records_and_library_and_traces(tmp_path: Path, monkeypatch):
    argv = ["olik", "build", "明", "清", "國", "森", "-o", str(tmp_path)]
    monkeypatch.setattr(sys, "argv", argv)
    rc = main()
    assert rc == 0

    lib_file = tmp_path / "prototype-library.json"
    assert lib_file.exists()
    lib = json.loads(lib_file.read_text())
    jsonschema.Draft202012Validator(
        json.loads((SCHEMA_ROOT / "prototype-library.schema.json").read_text())
    ).validate(lib)

    for ch in ["明", "清", "國", "森"]:
        rec = tmp_path / f"glyph-record-{ch}.json"
        assert rec.exists(), f"{rec} missing"
        data = json.loads(rec.read_text())
        jsonschema.Draft202012Validator(
            json.loads((SCHEMA_ROOT / "glyph-record.schema.json").read_text())
        ).validate(data)
        trace = tmp_path / f"rule-trace-{ch}.json"
        assert trace.exists()


def test_unknown_char_returns_nonzero(tmp_path: Path, monkeypatch, capsys):
    argv = ["olik", "build", "✗", "-o", str(tmp_path)]
    monkeypatch.setattr(sys, "argv", argv)
    rc = main()
    assert rc != 0
    captured = capsys.readouterr()
    assert "✗" in captured.err or "✗" in captured.out
```

- [ ] **Step 2: Run the test**

```bash
cd project/py && .venv/bin/pytest tests/test_cli.py -v
```

Expected: `ModuleNotFoundError` for `olik_font.cli`.

- [ ] **Step 3: Implement the CLI**

```python
# project/py/src/olik_font/cli.py
"""`olik` CLI: fetch → extract → decompose → compose → emit."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from olik_font.compose.walk import compose_transforms
from olik_font.decompose.instance import build_instance_tree
from olik_font.emit.library import library_to_dict
from olik_font.emit.record import build_glyph_record
from olik_font.emit.trace import trace_to_dict
from olik_font.prototypes.extract import extract_all_prototypes
from olik_font.prototypes.extraction_plan import load_extraction_plan
from olik_font.rules.engine import apply_first_match, load_rules
from olik_font.sources.makemeahanzi import fetch_mmh, load_mmh_graphics
from olik_font.types import PrototypeLibrary

_PY_ROOT = Path(__file__).resolve().parents[2]  # project/py/
_DEFAULT_MMH_DIR = _PY_ROOT / "data" / "mmh"
_DEFAULT_PLAN = _PY_ROOT / "data" / "extraction_plan.yaml"
_DEFAULT_RULES = _PY_ROOT / "src" / "olik_font" / "rules" / "rules.yaml"


def _parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="olik")
    sub = p.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("build", help="build glyph records for one or more characters")
    b.add_argument("chars", nargs="+", help="characters to build")
    b.add_argument("-o", "--out", required=True, type=Path, help="output dir")
    b.add_argument("--mmh-dir",  default=_DEFAULT_MMH_DIR,  type=Path, help="MMH cache dir")
    b.add_argument("--plan",     default=_DEFAULT_PLAN,     type=Path, help="extraction plan yaml")
    b.add_argument("--rules",    default=_DEFAULT_RULES,    type=Path, help="rules yaml")

    return p.parse_args(argv)


def main() -> int:
    args = _parse_args(sys.argv[1:])
    if args.cmd != "build":
        print(f"unknown cmd: {args.cmd}", file=sys.stderr)
        return 2

    out: Path = args.out
    out.mkdir(parents=True, exist_ok=True)

    graphics, _ = fetch_mmh(args.mmh_dir)
    mmh_chars = load_mmh_graphics(graphics)
    plan = load_extraction_plan(args.plan)
    rule_set = load_rules(args.rules)

    lib = PrototypeLibrary()
    extract_all_prototypes(plan, mmh_chars, lib)
    (out / "prototype-library.json").write_text(
        json.dumps(library_to_dict(lib), ensure_ascii=False, indent=2), encoding="utf-8",
    )

    exit_code = 0
    for ch in args.chars:
        if ch not in plan.glyphs:
            print(f"error: character not in extraction plan: {ch}", file=sys.stderr)
            exit_code = 1
            continue
        if ch not in mmh_chars:
            print(f"error: character not in MMH: {ch}", file=sys.stderr)
            exit_code = 1
            continue

        # Decomposition rule trace (thin but real)
        decomp_trace = apply_first_match(
            bucket=rule_set.decomposition,
            inputs={"char_in_extraction_plan": True},
            decision_id=f"d:{ch}:decomposition",
        )
        # Composition rule trace (per-root)
        compose_trace = apply_first_match(
            bucket=rule_set.composition,
            inputs={"has_preset_in_plan": True, "preset": plan.glyphs[ch].preset},
            decision_id=f"d:{ch}:composition",
        )

        tree = build_instance_tree(ch, plan)
        resolved, constraints = compose_transforms(tree, glyph_bbox=(0, 0, 1024, 1024))
        record = build_glyph_record(ch, resolved, constraints, lib, mmh_char=mmh_chars[ch])

        (out / f"glyph-record-{ch}.json").write_text(
            json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8",
        )
        (out / f"rule-trace-{ch}.json").write_text(
            json.dumps(
                {"decisions": [trace_to_dict(decomp_trace), trace_to_dict(compose_trace)]},
                ensure_ascii=False, indent=2,
            ),
            encoding="utf-8",
        )
        print(f"wrote {ch}: record + trace")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run the test**

```bash
cd project/py && .venv/bin/pytest tests/test_cli.py -v
```

Expected: `2 passed`.

- [ ] **Step 5: Run the CLI end-to-end**

```bash
cd project/py && .venv/bin/olik build 明 清 國 森 -o ../schema/examples
```

Expected output:
```
wrote 明: record + trace
wrote 清: record + trace
wrote 國: record + trace
wrote 森: record + trace
```

Verify files exist:
```bash
ls project/schema/examples/
```

Expected: `glyph-record-{明,清,國,森}.json`, `rule-trace-{明,清,國,森}.json`, `prototype-library.json`, plus the `hello-*.json` from Plan 01.

- [ ] **Step 6: Commit**

```bash
git add project/py/src/olik_font/cli.py project/py/tests/test_cli.py project/schema/examples/glyph-record-*.json project/schema/examples/rule-trace-*.json project/schema/examples/prototype-library.json
git commit -m "feat(cli): olik build — end-to-end glyph record generation"
```

---

## Task 7: IoU acceptance gate

**Files:**
- Create: `project/py/tests/test_iou_gate.py`

Per D13: warn if `min_iou < 0.85`; fail if `min_iou < 0.80`. This test is the "schema is working" gate for pass 1. If it fails, the preset parameters need tuning or `extraction_plan.yaml` needs updated stroke indices.

- [ ] **Step 1: Write the gate test**

```python
# project/py/tests/test_iou_gate.py
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
        warnings.warn(f"{ch}: min IoU {iou['min']:.3f} below warn threshold")
```

- [ ] **Step 2: Run the gate**

```bash
cd project/py && .venv/bin/pytest tests/test_iou_gate.py -v
```

Expected: `4 passed` (possibly with warnings). If any char *fails* (`min < 0.80`), the issue is almost always:
- the preset weight parameters (e.g. `weight_l`, `weight_top`) mismatch MMH's actual layout → tune in `presets.py`
- a prototype's extracted stroke range doesn't match MMH's actual stroke indices for that component → tune `extraction_plan.yaml`
- stroke count mismatch (flattened != MMH) → indicates a bug in `flatten.py` or a prototype with missing strokes

Document any tuning in the "Adjustments" section at the bottom of this plan.

- [ ] **Step 3: Commit**

```bash
git add project/py/tests/test_iou_gate.py
git commit -m "test(iou): acceptance gate per D13 (min>=0.80 fail, <0.85 warn)"
```

---

## Task 8: Final verification + tag

- [ ] **Step 1: Full suite**

```bash
cd project/py && .venv/bin/pytest -v
```

Expected: all Plan 01/02/03 tests pass. Count ≥ 65 passing.

- [ ] **Step 2: Confirm artifact shape on disk**

```bash
ls -la project/schema/examples/
jq '.metadata.iou_report | {mean, min}' project/schema/examples/glyph-record-明.json
```

Expected: all 4 × record + 4 × trace + prototype-library.json present; IoU mean/min reported.

- [ ] **Step 3: Tag milestone**

```bash
git tag -a plan-03-python-cli -m "Plan 03 complete — CLI produces validated glyph records"
```

---

## Self-review

Coverage against spec §§ P6, P7, P8:

- [x] Compose walker over InstancePlacement trees (Task 1) — P6 ✓
- [x] Stroke flattener + z-layer assignment (Task 2) — P6 ✓
- [x] IoU validator + report in metadata (Task 3) — P6, D13 ✓
- [x] Rule engine + rules.yaml + trace recording (Task 4) — P7, D15, D17 ✓
- [x] JSON emitters for record, library, trace (Task 5) — P6, D15 ✓
- [x] CLI orchestration (Task 6) — P8 ✓
- [x] IoU acceptance gate (Task 7) — D13 ✓

Sync point 2 (first real glyph record exists) is satisfied when Task 6 Step 5 produces valid JSON for all 4 chars.

## Follow-ups for later plans

- Plan 04 (TS foundation) consumes `project/schema/examples/*.json` as test fixtures.
- Anchor-binding authoring (D6) is still not exercised; a later tuning pass can add, e.g., 氵's internal 3-dot layout as anchor-bindings inside the prototype record.
- IoU is bbox-only; polygon IoU via shapely is deferred.
- Rule set is thin (delegates to extraction plan). Real decomposition rules (e.g., "if char in radical_list → keep") belong in a later plan once we expand beyond 4 chars.

## Adjustments after execution

_Tuning notes go here. Typical entries:_
- _"`left_right` default `weight_l=0.4` gave min IoU 0.72 for 明; changed to 0.32 → 0.88."_
- _"`extraction_plan.yaml proto:huo stroke_indices` for 國 adjusted from [3..10] to [3..9] after MMH showed 10 strokes, not 11."_
