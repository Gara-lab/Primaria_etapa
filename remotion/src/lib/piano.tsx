import React from 'react';
import { useCurrentFrame } from 'remotion';
import { FONT_BODY, FONT_DISPLAY } from '../fonts';
import { EASE_OUT, prog } from './shorts';

const SEMITONE: Record<string, number> = {
  C: 0, 'C#': 1, D: 2, 'D#': 3, E: 4, F: 5, 'F#': 6, G: 7, 'G#': 8, A: 9, 'A#': 10, B: 11,
};

export const toMidi = (note: string): number => {
  const m = note.match(/^([A-G]#?)(-?\d)$/);
  if (!m) throw new Error(`piano: bad note "${note}"`);
  return 12 * (parseInt(m[2], 10) + 1) + SEMITONE[m[1]];
};

export const toHz = (note: string): number => 440 * 2 ** ((toMidi(note) - 69) / 12);

const IS_BLACK = [false, true, false, true, false, false, true, false, true, false, true, false];
export const isBlack = (midi: number) => IS_BLACK[((midi % 12) + 12) % 12];

const whiteIndex = (midi: number, lowC: number) => {
  let n = 0;
  for (let m = lowC; m < midi; m++) if (!isBlack(m)) n++;
  return n;
};

export type Lit = { note: string; color: string; amount: number };

export const Keyboard: React.FC<{
  from?: string;
  to?: string;
  lit?: Lit[];
  x?: number;
  y?: number;
  w?: number;
  h?: number;
}> = ({ from = 'C3', to = 'C5', lit = [], x = 40, y = 980, w = 1000, h = 300 }) => {
  const lowC = toMidi(from);
  const high = toMidi(to);

  const whites: number[] = [];
  const blacks: number[] = [];
  for (let m = lowC; m <= high; m++) (isBlack(m) ? blacks : whites).push(m);

  const kw = w / whites.length;
  const bw = kw * 0.62;
  const bh = h * 0.62;

  const glow = (m: number): Lit | undefined => lit.find((l) => toMidi(l.note) === m && l.amount > 0.01);

  return (
    <div style={{ position: 'absolute', left: x, top: y, width: w, height: h }}>
      {whites.map((m) => {
        const g = glow(m);
        const a = g ? EASE_OUT(Math.min(1, g.amount)) : 0;
        const kx = whiteIndex(m, lowC) * kw;
        return (
          <div
            key={m}
            style={{
              position: 'absolute', left: kx, top: 0, width: kw - 2, height: h,
              background: g ? g.color : '#f7f7f4',
              opacity: g ? 0.35 + 0.65 * a : 1,
              borderRadius: '3px 3px 7px 7px',
              border: '1px solid #cfcfc9',
              transform: `translateY(${a * 5}px)`,
              boxShadow: g ? `0 0 ${28 * a}px ${g.color}` : '0 3px 0 #d9d9d3',
            }}
          />
        );
      })}
      {blacks.map((m) => {
        const g = glow(m);
        const a = g ? EASE_OUT(Math.min(1, g.amount)) : 0;
        const kx = whiteIndex(m, lowC) * kw - bw / 2;
        return (
          <div
            key={m}
            style={{
              position: 'absolute', left: kx, top: 0, width: bw, height: bh,
              background: g ? g.color : '#1c1e22',
              opacity: g ? 0.5 + 0.5 * a : 1,
              borderRadius: '2px 2px 5px 5px',
              transform: `translateY(${a * 4}px)`,
              boxShadow: g ? `0 0 ${24 * a}px ${g.color}` : '0 3px 6px rgba(0,0,0,0.5)',
              zIndex: 2,
            }}
          />
        );
      })}
    </div>
  );
};

export const ChordChip: React.FC<{
  label: string;
  roman?: string;
  x: number;
  y: number;
  color?: string;
  at?: number;
  active?: number;
  w?: number;
}> = ({ label, roman, x, y, color = '#f5d76e', at = 0, active = 0, w = 200 }) => {
  const frame = useCurrentFrame();
  const p = EASE_OUT(prog(frame, at, at + 12));
  if (p <= 0.01) return null;
  const a = Math.max(0, Math.min(1, active));
  return (
    <div
      style={{
        position: 'absolute', left: x, top: y, width: w,
        opacity: (0.4 + 0.6 * a) * p,
        transform: `translateY(${(1 - p) * 14}px) scale(${(0.94 + 0.06 * p) * (1 + 0.08 * a)})`,
        textAlign: 'center',
      }}
    >
      <div
        style={{
          fontFamily: FONT_DISPLAY, fontWeight: 700, fontSize: 62, lineHeight: 1.05,
          color: a > 0.35 ? '#0f1216' : color,
          background: a > 0.35 ? color : 'rgba(0,0,0,0.35)',
          border: `3px solid ${color}${a > 0.35 ? '' : '66'}`,
          borderRadius: 18, padding: '8px 0',
          boxShadow: a > 0.35 ? `0 0 ${40 * a}px ${color}88` : 'none',
        }}
      >
        {label}
      </div>
      {roman ? (
        <div
          style={{
            fontFamily: FONT_BODY, fontWeight: 600, fontSize: 30, letterSpacing: 3,
            color: 'rgba(255,255,255,0.72)', marginTop: 10,
          }}
        >
          {roman}
        </div>
      ) : null}
    </div>
  );
};

export const SongStamp: React.FC<{
  title: string;
  artist: string;
  x?: number;
  y: number;
  at: number;
  until?: number;
  color?: string;
}> = ({ title, artist, x = 60, y, at, until, color = '#ffffff' }) => {
  const frame = useCurrentFrame();
  const p = EASE_OUT(prog(frame, at, at + 10));
  const out = until === undefined ? 1 : 1 - prog(frame, until, until + 12);
  const o = p * out;
  if (o <= 0.01) return null;
  return (
    <div
      style={{
        position: 'absolute', left: x, top: y, right: 60,
        opacity: o,
        transform: `translateX(${(1 - p) * -26}px)`,
        display: 'flex', alignItems: 'baseline', gap: 16,
      }}
    >
      <span style={{ fontFamily: FONT_DISPLAY, fontWeight: 700, fontSize: 46, color, letterSpacing: 0.5 }}>
        {title}
      </span>
      <span style={{ fontFamily: FONT_BODY, fontWeight: 500, fontSize: 30, color: 'rgba(255,255,255,0.55)' }}>
        {artist}
      </span>
    </div>
  );
};

export const strike = (frame: number, at: number, fps = 30, release = 1.5): number => {
  if (frame < at) return 0;
  const t = (frame - at) / fps;
  const atk = Math.min(1, t / 0.05);
  return atk * Math.exp(-t / release);
};
