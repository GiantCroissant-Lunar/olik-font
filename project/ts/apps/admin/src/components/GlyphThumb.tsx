import { memo } from "react";

interface GlyphThumbProps {
  char: string;
  size?: number;
}

/**
 * Simple char thumbnail. Plan 10 uses the system CJK font as a proxy
 * for the composed shape - the list grid is a pick-from-queue surface,
 * not a final-output preview. The detail view renders the real
 * composed SVG (Task 9).
 */
export const GlyphThumb = memo(function GlyphThumb({
  char,
  size = 36,
}: GlyphThumbProps) {
  const svg = encodeURIComponent(
    `<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 ${size} ${size}"><text x="50%" y="50%" dominant-baseline="central" text-anchor="middle" font-size="${size * 0.85}" font-family="system-ui, 'Noto Sans CJK TC', sans-serif">${char}</text></svg>`,
  );

  return (
    <span
      aria-label={`${char} thumbnail`}
      role="img"
      style={{
        display: "inline-block",
        width: size,
        height: size,
        backgroundImage: `url("data:image/svg+xml,${svg}")`,
        backgroundPosition: "center",
        backgroundRepeat: "no-repeat",
        backgroundSize: "contain",
      }}
    />
  );
});
