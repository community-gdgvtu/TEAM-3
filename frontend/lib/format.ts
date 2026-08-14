/** Shared number formatting for dashboard tiles. */

/** Compact human number: 12.3k, 1.2M, 4.56, etc. */
export function formatNumber(v: number): string {
  const abs = Math.abs(v);
  if (abs >= 1_000_000) return `${(v / 1_000_000).toFixed(2)}M`;
  if (abs >= 10_000) return `${(v / 1_000).toFixed(1)}k`;
  if (abs >= 1_000) return `${(v / 1_000).toFixed(2)}k`;
  if (abs >= 100) return v.toFixed(0);
  if (abs >= 1) return v.toFixed(1);
  return v.toFixed(2);
}

/** Signed percentage, e.g. +4.2% / −1.0%. */
export function formatSignedPct(frac: number): string {
  const pct = frac * 100;
  const sign = pct > 0 ? "+" : pct < 0 ? "−" : "";
  return `${sign}${Math.abs(pct).toFixed(1)}%`;
}
