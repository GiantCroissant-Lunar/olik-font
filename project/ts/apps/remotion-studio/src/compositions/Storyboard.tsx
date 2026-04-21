import * as React from "react";
import { Sequence } from "remotion";
import type { GlyphBundle } from "@olik/glyph-loader";
import { CharacterAnim } from "./CharacterAnim.js";
import { DecompositionTree } from "./DecompositionTree.js";
import { LayerZDepth } from "./LayerZDepth.js";
import { PrototypeGraph } from "./PrototypeGraph.js";
import { VirtualCoord } from "./VirtualCoord.js";

export interface StoryboardProps extends Record<string, unknown> {
  bundle: GlyphBundle;
  chars: readonly string[];
  framesPerStroke: number;
  sceneFrames: number;
}

export const Storyboard: React.FC<StoryboardProps> = ({
  bundle, chars, framesPerStroke, sceneFrames,
}) => {
  let cursor = 0;
  const scenes: React.ReactNode[] = [];

  for (const ch of chars) {
    scenes.push(
      <Sequence key={`anim-${ch}`} from={cursor} durationInFrames={sceneFrames}>
        <CharacterAnim bundle={bundle} char={ch} framesPerStroke={framesPerStroke} />
      </Sequence>,
    );
    cursor += sceneFrames;

    scenes.push(
      <Sequence key={`tree-${ch}`} from={cursor} durationInFrames={sceneFrames}>
        <DecompositionTree bundle={bundle} char={ch} framesPerStroke={framesPerStroke} />
      </Sequence>,
    );
    cursor += sceneFrames;

    scenes.push(
      <Sequence key={`layer-${ch}`} from={cursor} durationInFrames={sceneFrames}>
        <LayerZDepth bundle={bundle} char={ch} />
      </Sequence>,
    );
    cursor += sceneFrames;

    scenes.push(
      <Sequence key={`coord-${ch}`} from={cursor} durationInFrames={sceneFrames}>
        <VirtualCoord bundle={bundle} char={ch} />
      </Sequence>,
    );
    cursor += sceneFrames;
  }

  scenes.push(
    <Sequence key="graph-final" from={cursor} durationInFrames={sceneFrames}>
      <PrototypeGraph bundle={bundle} />
    </Sequence>,
  );

  return <>{scenes}</>;
};
