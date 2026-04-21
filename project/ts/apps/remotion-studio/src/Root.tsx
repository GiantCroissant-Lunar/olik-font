import * as React from 'react';
import {Composition} from 'remotion';

export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="Placeholder"
      component={() => <div style={{background: '#000', width: 1280, height: 720}} />}
      durationInFrames={30}
      fps={30}
      width={1280}
      height={720}
    />
  );
};
