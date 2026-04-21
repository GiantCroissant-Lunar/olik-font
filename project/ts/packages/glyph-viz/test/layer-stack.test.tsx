import { render } from "@testing-library/react";
import { describe, expect, test } from "vitest";
import type { RenderLayer, StrokeInstance } from "@olik/glyph-schema";
import { LayerStack } from "../src/layer-stack.js";

const layers: RenderLayer[] = [
  { name: "skeleton", z_min: 0, z_max: 9 },
  { name: "stroke_body", z_min: 10, z_max: 49 },
  { name: "stroke_edge", z_min: 50, z_max: 69 },
];

const strokes: StrokeInstance[] = [
  {
    id: "s1",
    instance_id: "inst:a",
    order: 0,
    path: "M 0 0 L 10 0",
    median: [
      [0, 0],
      [10, 0],
    ],
    bbox: [0, 0, 10, 0],
    z: 20,
    role: "horizontal",
  },
  {
    id: "s2",
    instance_id: "inst:a",
    order: 1,
    path: "M 0 5 L 10 5",
    median: [
      [0, 5],
      [10, 5],
    ],
    bbox: [0, 5, 10, 5],
    z: 22,
    role: "horizontal",
  },
  {
    id: "s3",
    instance_id: "inst:b",
    order: 0,
    path: "M 5 0 L 5 10",
    median: [
      [5, 0],
      [5, 10],
    ],
    bbox: [5, 0, 5, 10],
    z: 55,
    role: "vertical",
  },
];

describe("LayerStack", () => {
  test("renders one panel per layer", () => {
    const { container } = render(
      <svg>
        <LayerStack layers={layers} strokes={strokes} panelHeight={100} />
      </svg>,
    );
    const panels = container.querySelectorAll("g.olik-layer-panel");
    expect(panels.length).toBe(3);
  });

  test("assigns strokes to correct layers by z", () => {
    const { container } = render(
      <svg>
        <LayerStack layers={layers} strokes={strokes} panelHeight={100} />
      </svg>,
    );
    const panels = container.querySelectorAll("g.olik-layer-panel");
    expect(panels[0].querySelectorAll("path").length).toBe(0);
    expect(panels[1].querySelectorAll("path").length).toBe(2);
    expect(panels[2].querySelectorAll("path").length).toBe(1);
  });

  test("panel labels show layer name + stroke count", () => {
    const { container } = render(
      <svg>
        <LayerStack layers={layers} strokes={strokes} panelHeight={100} />
      </svg>,
    );
    expect(container.textContent).toContain("stroke_body");
    expect(container.textContent).toContain("(2)");
  });
});
