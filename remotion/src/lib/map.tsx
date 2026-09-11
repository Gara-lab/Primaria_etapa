import React from 'react';
import { Country, Ring, WORLD } from './geo/world';
import { FONT_BODY, FONT_DISPLAY } from '../fonts';

export type { Country, Ring };

export const MAX_LAT = 85.05;

export const mercY = (lat: number): number => {
  const c = Math.max(-MAX_LAT, Math.min(MAX_LAT, lat));
  return Math.log(Math.tan(Math.PI / 4 + (c * Math.PI) / 180 / 2));
};

export type MapScale = {
  px: (lon: number, lat: number) => [number, number];
  box: { x: number; y: number; w: number; h: number };
  k: number;
};

export const makeMapScale = (
  lonRange: [number, number],
  latRange: [number, number],
  box: { x: number; y: number; w: number },
): MapScale => {
  const x0 = (lonRange[0] * Math.PI) / 180;
  const x1 = (lonRange[1] * Math.PI) / 180;
  const k = box.w / (x1 - x0);
  const yTop = mercY(latRange[1]);
  const yBot = mercY(latRange[0]);
  const h = (yTop - yBot) * k;
  return {
    k,
    box: { ...box, h },
    px: (lon, lat) => [box.x + ((lon * Math.PI) / 180 - x0) * k, box.y + (yTop - mercY(lat)) * k],
  };
};

export type Move = { toLon: number; toLat: number };

const COS_MIN = Math.cos((MAX_LAT * Math.PI) / 180);
const cosLat = (lat: number) => Math.max(COS_MIN, Math.cos((lat * Math.PI) / 180));

const transportPt = (
  lon: number,
  lat: number,
  cLon: number,
  cLat: number,
  dLon: number,
  dLat: number,
  t: number,
): [number, number] => {
  const latN = lat + dLat * t;
  const k = cosLat(lat) / cosLat(latN);
  const lonN = cLon + dLon * t + (lon - cLon) * k;
  return [lonN, latN];
};

const ringPath = (s: MapScale, ring: Ring, tp: (lon: number, lat: number) => [number, number]): string => {
  let d = '';
  for (let i = 0; i < ring.length; i++) {
    const [lon, lat] = tp(ring[i][0], ring[i][1]);
    const [x, y] = s.px(lon, lat);
    d += `${i === 0 ? 'M' : 'L'}${x.toFixed(1)} ${y.toFixed(1)}`;
  }
  return d + 'Z';
};

export const countryPath = (s: MapScale, c: Country): string =>
  c.rings.map((r) => ringPath(s, r, (lon, lat) => [lon, lat])).join(' ');

const mover = (c: Country, m: Move, t: number) => {
  const [cLon, cLat] = centroid(c);
  const dLon = m.toLon - cLon;
  const dLat = m.toLat - cLat;
  return (lon: number, lat: number) => transportPt(lon, lat, cLon, cLat, dLon, dLat, t);
};

export const movedPath = (s: MapScale, c: Country, m: Move, t: number): string =>
  c.rings.map((r) => ringPath(s, r, mover(c, m, t))).join(' ');

export const movedCentroid = (c: Country, m: Move, t: number): [number, number] => {
  const [cLon, cLat] = centroid(c);
  return [cLon + (m.toLon - cLon) * t, cLat + (m.toLat - cLat) * t];
};

export const projectedArea = (s: MapScale, c: Country, m?: Move, t = 0): number => {
  const tp = m ? mover(c, m, t) : (lon: number, lat: number): [number, number] => [lon, lat];
  let total = 0;
  for (const ring of c.rings) {
    let a = 0;
    for (let i = 0; i < ring.length; i++) {
      const [lo1, la1] = tp(ring[i][0], ring[i][1]);
      const [lo2, la2] = tp(ring[(i + 1) % ring.length][0], ring[(i + 1) % ring.length][1]);
      const [x1, y1] = s.px(lo1, la1);
      const [x2, y2] = s.px(lo2, la2);
      a += x1 * y2 - x2 * y1;
    }
    total += Math.abs(a) / 2;
  }
  return total;
};

export const inflation = (s: MapScale, c: Country): number => {
  const [cLon] = centroid(c);
  const equator: Move = { toLon: cLon, toLat: 0 };
  return projectedArea(s, c) / Math.max(1e-9, projectedArea(s, c, equator, 1));
};

export const centroid = (c: Country): [number, number] => {
  let lo = 0;
  let la = 0;
  let n = 0;
  for (const ring of c.rings) {
    for (const [x, y] of ring) {
      lo += x;
      la += y;
      n++;
    }
  }
  return [lo / n, la / n];
};


export const WorldLayer: React.FC<{
  scale: MapScale;
  except?: string[];
  fill?: string;
  stroke?: string;
  opacity?: number;
}> = ({ scale, except = [], fill = '#233042', stroke = '#31425a', opacity = 1 }) => (
  <g opacity={opacity}>
    {WORLD.filter((c) => c.cont !== 'Antarctica' && !except.includes(c.name)).map((c) => (
      <path key={c.name} d={countryPath(scale, c)} fill={fill} stroke={stroke} strokeWidth={1} />
    ))}
  </g>
);

export const CountryShape: React.FC<{
  scale: MapScale;
  country: Country;
  move?: Move;
  t?: number;
  fill: string;
  stroke?: string;
  strokeWidth?: number;
  opacity?: number;
  glow?: boolean;
}> = ({ scale, country, move, t = 0, fill, stroke, strokeWidth = 2.5, opacity = 1, glow = false }) => (
  <path
    d={move ? movedPath(scale, country, move, t) : countryPath(scale, country)}
    fill={fill}
    stroke={stroke ?? fill}
    strokeWidth={strokeWidth}
    strokeLinejoin="round"
    opacity={opacity}
    style={glow ? { filter: `drop-shadow(0 0 18px ${fill})` } : undefined}
  />
);

export const Graticule: React.FC<{
  scale: MapScale;
  lats?: number[];
  color?: string;
  opacity?: number;
}> = ({ scale, lats = [-60, -30, 0, 30, 60, 80], color = '#5b7a99', opacity = 0.25 }) => {
  const { box } = scale;
  return (
    <g opacity={opacity}>
      {lats.map((lat) => {
        const [, y] = scale.px(0, lat);
        const eq = lat === 0;
        return (
          <line
            key={lat}
            x1={box.x}
            x2={box.x + box.w}
            y1={y}
            y2={y}
            stroke={color}
            strokeWidth={eq ? 2.5 : 1.5}
            strokeDasharray={eq ? undefined : '8 10'}
          />
        );
      })}
    </g>
  );
};

export const MapLabel: React.FC<{
  x: number;
  y: number;
  title: string;
  stat?: string;
  color: string;
  size?: number;
  opacity?: number;
  scaleUp?: number;
  anchor?: 'middle' | 'start' | 'end';
}> = ({ x, y, title, stat, color, size = 34, opacity = 1, scaleUp = 0, anchor = 'middle' }) => (
  <div
    style={{
      position: 'absolute',
      left: x,
      top: y,
      transform: `translate(${anchor === 'middle' ? '-50%' : anchor === 'end' ? '-100%' : '0'}, -50%) scale(${
        1 + 0.12 * scaleUp
      })`,
      opacity,
      background: 'rgba(13,17,23,0.86)',
      border: `2px solid ${color}${scaleUp > 0.5 ? 'cc' : '55'}`,
      borderRadius: 14,
      padding: '8px 16px',
      textAlign: 'center',
      whiteSpace: 'nowrap',
    }}
  >
    <div
      style={{
        fontFamily: FONT_BODY,
        fontWeight: 700,
        fontSize: size * 0.72,
        letterSpacing: 3,
        textTransform: 'uppercase',
        color,
      }}
    >
      {title}
    </div>
    {stat ? (
      <div style={{ fontFamily: FONT_DISPLAY, fontWeight: 700, fontSize: size, color: '#fff', marginTop: 2 }}>
        {stat}
      </div>
    ) : null}
  </div>
);
