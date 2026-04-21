import { render } from "@testing-library/react";
import { describe, expect, test } from "vitest";
import { StrokePath } from "../src/stroke-path.js";

describe("StrokePath", () => {
  test("renders outline and median paths", () => {
    const { container } = render(
      <svg>
        <StrokePath
          outlinePath="M 0 0 L 10 0 L 10 10 L 0 10 Z"
          median={[[5, 0], [5, 10]]}
          progress={1}
        />
      </svg>,
    );
    const paths = container.querySelectorAll("path");
    expect(paths.length).toBe(2);
  });

  test("progress=0 hides the median stroke via dash offset", () => {
    const { container } = render(
      <svg>
        <StrokePath outlinePath="M 0 0 L 1 0" median={[[0, 0], [1, 0]]} progress={0} />
      </svg>,
    );
    const medianPath = container.querySelectorAll("path")[1];
    const dashOffset = Number(medianPath.getAttribute("stroke-dashoffset"));
    expect(dashOffset).toBeGreaterThan(0);
  });

  test("progress=1 fully draws the median", () => {
    const { container } = render(
      <svg>
        <StrokePath outlinePath="M 0 0 L 1 0" median={[[0, 0], [1, 0]]} progress={1} />
      </svg>,
    );
    const medianPath = container.querySelectorAll("path")[1];
    expect(Number(medianPath.getAttribute("stroke-dashoffset"))).toBe(0);
  });

  test("single-point median treated as zero-length dash", () => {
    const { container } = render(
      <svg>
        <StrokePath outlinePath="M 0 0 Z" median={[[0, 0]]} progress={1} />
      </svg>,
    );
    expect(container.querySelectorAll("path").length).toBe(2);
  });
});
