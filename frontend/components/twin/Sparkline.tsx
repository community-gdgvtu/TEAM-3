"use client";

/**
 * Tiny trajectory sparkline with a visible uncertainty band (SPEC §9): the band
 * area (low→high) sits behind the central line, and a marker highlights the
 * selected checkpoint. Pure SVG, no chart lib — keeps the tile lightweight and
 * the widening band unmistakable.
 */

import type { MetricPoint } from "../../lib/api";

export interface SparklineProps {
  points: MetricPoint[];
  index: number;
  color?: string;
  width?: number;
  height?: number;
}

export default function Sparkline({
  points,
  index,
  color = "#4f8cff",
  width = 220,
  height = 56,
}: SparklineProps) {
  if (points.length === 0) return null;

  const pad = 4;
  const n = points.length;
  let lo = Infinity;
  let hi = -Infinity;
  for (const p of points) {
    lo = Math.min(lo, p.low);
    hi = Math.max(hi, p.high);
  }
  if (lo === hi) {
    hi = lo + 1;
    lo -= 1;
  }

  const x = (i: number) =>
    n === 1 ? width / 2 : pad + (i / (n - 1)) * (width - 2 * pad);
  const y = (v: number) =>
    height - pad - ((v - lo) / (hi - lo)) * (height - 2 * pad);

  const bandTop = points.map((p, i) => `${x(i)},${y(p.high)}`);
  const bandBottom = points
    .slice()
    .reverse()
    .map((p, ri) => {
      const i = n - 1 - ri;
      return `${x(i)},${y(p.low)}`;
    });
  const bandPath = `${bandTop.join(" ")} ${bandBottom.join(" ")}`;
  const linePath = points.map((p, i) => `${x(i)},${y(p.value)}`).join(" ");

  const sel = points[Math.min(index, n - 1)];
  const selX = x(Math.min(index, n - 1));
  const selY = y(sel.value);

  return (
    <svg
      className="sparkline"
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      role="img"
      aria-label="Metric trajectory with uncertainty band"
    >
      <polygon points={bandPath} fill={color} fillOpacity={0.16} stroke="none" />
      <polyline
        points={linePath}
        fill="none"
        stroke={color}
        strokeWidth={1.75}
        strokeLinejoin="round"
        strokeLinecap="round"
      />
      <line
        x1={selX}
        y1={pad}
        x2={selX}
        y2={height - pad}
        stroke={color}
        strokeOpacity={0.35}
        strokeWidth={1}
      />
      <circle cx={selX} cy={selY} r={3.2} fill={color} stroke="#0b1020" strokeWidth={1} />
    </svg>
  );
}
