import { memo } from "react";

interface MmhSvgProps {
  /** MMH stroke path-d strings from glyph.mmh_strokes. */
  strokes: readonly string[];
  canvas?: number;
  size?: number;
  background?: string;
}

/**
 * Renders the MMH reference strokes. Shares the same coord space and
 * flip as GlyphSvg so the two panels are visually comparable - any
 * structural difference indicates a real extraction issue rather than
 * a coordinate-frame mismatch.
 */
export const MmhSvg = memo(function MmhSvg({
  strokes,
  canvas = 1024,
  size = 512,
  background = "#f8fafc",
}: MmhSvgProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox={`0 0 ${canvas} ${canvas}`}
      style={{ background, display: "block" }}
    >
      <g transform={`translate(0, ${canvas}) scale(1, -1)`}>
        {strokes.map((d, i) => (
          <path key={i} d={d} fill="#334155" stroke="none" />
        ))}
      </g>
    </svg>
  );
});
