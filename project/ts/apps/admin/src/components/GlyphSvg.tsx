import { memo } from "react";

interface GlyphSvgProps {
  /** Path-d strings from glyph.stroke_instances (composed output). */
  strokes: readonly string[];
  /** SVG viewbox square side length in canonical units (default 1024). */
  canvas?: number;
  /** Rendered size in CSS pixels. */
  size?: number;
  /** CSS background color for contrast. */
  background?: string;
}

/**
 * Renders composed stroke paths with the y-up to y-down flip applied
 * at the group level, matching preview-glyph.py and the existing
 * quickview renderer.
 */
export const GlyphSvg = memo(function GlyphSvg({
  strokes,
  canvas = 1024,
  size = 512,
  background = "#ffffff",
}: GlyphSvgProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox={`0 0 ${canvas} ${canvas}`}
      style={{ background, display: "block" }}
    >
      <g transform={`translate(0, ${canvas}) scale(1, -1)`}>
        {strokes.map((d, i) => (
          <path key={i} d={d} fill="#0f172a" stroke="none" />
        ))}
      </g>
    </svg>
  );
});
