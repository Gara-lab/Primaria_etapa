import React from 'react';
import { AbsoluteFill, Img, staticFile, useCurrentFrame } from 'remotion';
import { EASE_INOUT, prog } from './shorts';

const MOVES = [
  { s: [1.12, 1.2], x: [0, -2], y: [0, -1.5] },
  { s: [1.2, 1.12], x: [1.5, 0], y: [1, 0] },
  { s: [1.12, 1.2], x: [-2, 1.5], y: [0, 0] },
  { s: [1.18, 1.12], x: [0, 0], y: [-1.5, 1] },
  { s: [1.12, 1.19], x: [2, -1], y: [0.5, -1] },
  { s: [1.16, 1.22], x: [0, 1], y: [1, -1] },
] as const;

export const KenBurnsImage: React.FC<{
  src: string;
  dur: number;
  variant?: number;
  fadeIn?: number;
}> = ({ src, dur, variant = 0, fadeIn = 14 }) => {
  const frame = useCurrentFrame();
  const m = MOVES[variant % MOVES.length];
  const p = EASE_INOUT(prog(frame, 0, dur));
  const scale = m.s[0] + (m.s[1] - m.s[0]) * p;
  const tx = m.x[0] + (m.x[1] - m.x[0]) * p;
  const ty = m.y[0] + (m.y[1] - m.y[0]) * p;
  const opacity = fadeIn > 0 ? prog(frame, 0, fadeIn) : 1;
  return (
    <AbsoluteFill style={{ opacity }}>
      <Img
        src={staticFile(src)}
        style={{
          position: 'absolute',
          width: '100%',
          height: '100%',
          objectFit: 'cover',
          transform: `scale(${scale}) translate(${tx}%, ${ty}%)`,
          transformOrigin: 'center center',
        }}
      />
    </AbsoluteFill>
  );
};

export const StoryVignette: React.FC<{ strength?: number }> = ({ strength = 0.42 }) => (
  <AbsoluteFill
    style={{
      background: `radial-gradient(ellipse 108% 82% at 50% 44%, transparent 46%, rgba(20,16,30,${strength}) 100%)`,
      pointerEvents: 'none',
    }}
  />
);
