import * as React from "react";
import { Composition, continueRender, delayRender } from "remotion";
import type { GlyphBundle } from "@olik/glyph-loader";
import { CharacterAnim, type CharacterAnimProps } from "./compositions/CharacterAnim.js";
import { loadSeedBundle, SEED_CHARS } from "./load-records.js";
import { totalStrokeFrames } from "./timing.js";

const FRAMES_PER_STROKE = 12;

export const RemotionRoot: React.FC = () => {
  const [bundle, setBundle] = React.useState<GlyphBundle | null>(null);
  const [handle] = React.useState(() => delayRender("load-bundle"));

  React.useEffect(() => {
    loadSeedBundle()
      .then((b) => {
        setBundle(b);
        continueRender(handle);
      })
      .catch((err) => {
        console.error("load bundle failed:", err);
        continueRender(handle);
      });
  }, [handle]);

  if (!bundle) return null;

  return (
    <>
      {SEED_CHARS.map((ch) => {
        const strokes = bundle.records[ch]?.stroke_instances.length ?? 8;
        const duration = totalStrokeFrames({
          strokeCount: strokes,
          framesPerStroke: FRAMES_PER_STROKE,
        }) + 30;
        return (
          <Composition<any, CharacterAnimProps>
            key={`char-${ch}`}
            id={`CharacterAnim-${ch}`}
            component={CharacterAnim}
            durationInFrames={duration}
            fps={30}
            width={1280}
            height={720}
            defaultProps={{ bundle, char: ch, framesPerStroke: FRAMES_PER_STROKE, showGrid: false }}
          />
        );
      })}
    </>
  );
};
