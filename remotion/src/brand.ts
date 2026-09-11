import { Easing } from 'remotion';

export const BRAND = {
  wordmark: ['Your', 'Channel', ''] as readonly string[],
  signoff: 'See you in the next one',
} as const;

export const COLORS = {
  accent: '#6366F1',
  accent2: '#9b7cc4',
  signal: '#4db8a8',
  signalAlt: '#4ecdc4',
  warn: '#f5d76e',
  danger: '#e8879f',
  ink: '#1a1a2e',
  muted: '#6b6b7b',
  paper: '#fffef7',
  cream: '#faf8f5',
  line: '#e7e3da',
  d900: '#0d1117',
  d800: '#161b22',
  d600: '#30363d',
  d400: '#8b949e',
  d300: '#c9d1d9',
} as const;

export const GRADIENT = `linear-gradient(120deg, ${COLORS.accent}, ${COLORS.accent2}, ${COLORS.signal})`;

export const RADIUS = { card: 16, panel: 14, window: 10, pill: 999 } as const;

export const SHADOW = {
  soft: '0 8px 32px rgba(26,26,46,0.10)',
  card: '0 10px 40px rgba(26,26,46,0.08)',
} as const;

export const EASINGS = {
  easeOut: Easing.bezier(0.33, 1, 0.68, 1),
  easeIn: Easing.bezier(0.32, 0, 0.67, 0),
  easeInOut: Easing.bezier(0.37, 0, 0.63, 1),
  overshoot: Easing.bezier(0.34, 1.4, 0.64, 1),
} as const;
