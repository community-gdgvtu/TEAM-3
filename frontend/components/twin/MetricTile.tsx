"use client";

/**
 * One outcome dashboard tile (SPEC §27): headline value at the selected
 * checkpoint, a provenance chip, a visible uncertainty band (via Sparkline +
 * ± range), and deltas.
 *
 * Two deltas are shown honestly:
 *   - "vs T0" — baseline drift from implementation to the selected horizon
 *     (always available from the World-A series).
 *   - "vs baseline" — the World-B − World-A policy effect. Until `/simulate` is
 *     wired this reads "simulate a policy", never a fabricated number (SPEC §34).
 *
 * Metrics with no baseline series yet (Equity, Support) render an explicit
 * "awaiting /simulate" placeholder instead of inventing a value.
 */

import type { MetricSeries } from "../../lib/api";
import { formatNumber, formatSignedPct } from "../../lib/format";
import Sparkline from "./Sparkline";

export interface MetricTileProps {
  title: string;
  /** Baseline (World-A) series for this metric, or null if not yet modelled. */
  series: MetricSeries | null;
  index: number;
  color?: string;
  /** Whether a rising value is a good outcome (transit) or bad (CO₂, traffic). */
  higherIsBetter?: boolean;
  /** Reason shown when `series` is null (e.g. depends on /simulate). */
  placeholderNote?: string;
}

export default function MetricTile({
  title,
  series,
  index,
  color = "#4f8cff",
  higherIsBetter = false,
  placeholderNote = "Awaiting /simulate",
}: MetricTileProps) {
  if (!series || series.points.length === 0) {
    return (
      <div className="tile tile-empty">
        <div className="tile-head">
          <span className="tile-title">{title}</span>
          <span className="tag placeholder">Awaiting model</span>
        </div>
        <div className="tile-empty-body">{placeholderNote}</div>
      </div>
    );
  }

  const i = Math.min(index, series.points.length - 1);
  const pt = series.points[i];
  const t0 = series.points[0];
  const bandRel = pt.value !== 0 ? (pt.high - pt.low) / 2 / Math.abs(pt.value) : 0;
  const driftFrac = t0.value !== 0 ? (pt.value - t0.value) / Math.abs(t0.value) : 0;
  const driftUp = pt.value > t0.value;
  const driftGood = driftUp === higherIsBetter;

  return (
    <div className="tile">
      <div className="tile-head">
        <span className="tile-title">{title}</span>
        <span className={`tag ${series.tag.toLowerCase()}`}>{series.tag}</span>
      </div>

      <div className="tile-value">
        {formatNumber(pt.value)}
        <span className="tile-unit">{series.unit}</span>
      </div>

      <div className="tile-band">
        ±{(bandRel * 100).toFixed(1)}% band · {formatNumber(pt.low)}–
        {formatNumber(pt.high)}
      </div>

      <Sparkline points={series.points} index={i} color={color} />

      <div className="tile-deltas">
        <span className="delta">
          <span className="delta-label">vs T0</span>
          <span
            className={`delta-val ${i === 0 ? "muted" : driftGood ? "down" : "up"}`}
          >
            {i === 0 ? "—" : formatSignedPct(driftFrac)}
          </span>
        </span>
        <span className="delta">
          <span className="delta-label">vs baseline</span>
          <span className="delta-val muted">simulate a policy</span>
        </span>
      </div>
    </div>
  );
}
