import React from 'react';
import { Composition } from 'remotion';
import { shots } from './registry.gen';

export const RemotionRoot: React.FC = () => {
  return (
    <>
      {shots.map(({ Comp, config }) => (
        <Composition
          key={config.id}
          id={config.id}
          component={Comp as React.FC}
          durationInFrames={Math.max(1, Math.round(config.durationInSeconds * config.fps))}
          fps={config.fps}
          width={config.width}
          height={config.height}
        />
      ))}
    </>
  );
};
