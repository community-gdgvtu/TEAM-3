"use client";

/**
 * One outcome dashboard tile (SPEC §27): headline value at the selected
 * checkpoint, a provenance chip, a visible uncertainty band (via Sparkline +
 * ± range), and deltas.
 *
 * Two modes:
 *   - Baseline only (no simulation): shows the World-A value + band, a "vs T0"
 *     drift, and a "vs baseline" placeholder ("simulate a policy") — never a
 *     fabricated policy effect.
 *   - Simulation present (`delta` supplied): shows the World-B value, the REAL
 *     Δ(B−A) vs baseline (value + %), and a sparkline of the policy effect with
 *     its widening band. This is what "apply amendment + re-simulate" updates
 *     (SPEC §29). Every number is Simulated (SPEC §34).
 *
 * Metrics with no series (Equity, Support) render an explicit placeholder.
 */

import type { DeltaSeries, MetricSeries } from "../../lib/api";
import { formatNumber, formatSignedPct } from "../../lib/format";
import Sparkline from "./Sparkline";

export interface MetricTileProps {
  title: string;
  /** Baseline (World-A) series for this metric, or null if not yet modelled. */
  series: MetricSeries | null;
  /** Δ(B−A) series for this metric when a simulation is active, else null. */
  delta?: DeltaSeries | null;
  index: number;
  color?: string;
  /** Whether a rising value is a good outcome (transit) or bad (CO₂, traffic). */
  higherIsBetter?: boolean;
  /** Reason shown when there is no series (e.g. depends on /simulate). */
  placeholderNote?: string;
  /** Dotted metric key for the evidence trace, e.g. `traffic.daily_vehicle_km`. */
  metricKey?: string | null;
  /** Open the evidence drawer for `metricKey` (only wired when a policy exists). */
  onExplain?: (metricKey: string) => void;
}

export default function MetricTile({
  title,
  series,
  delta = null,
  index,
  color = "#4f8cff",
  higherIsBetter = false,
  placeholderNote = "Awaiting /simulate",
  metricKey = null,
  onExplain,
}: MetricTileProps) {
  const canExplain = Boolean(metricKey && onExplain);
  const explain = () => {
    if (metricKey && onExplain) onExplain(metricKey);
  };
  // --- Simulation mode: show World B + real Δ vs baseline ------------------
  if (delta && delta.points.length > 0) {
    const i = Math.min(index, delta.points.length - 1);
    const dp = delta.points[i];
    const effectPts = delta.points.map((p) => ({
      t_months: p.t_months,
      value: p.delta,
      low: p.low,
      high: p.high,
    }));
    const good = dp.delta > 0 === higherIsBetter;
    const deltaPct = dp.delta_pct;

    return (
      <div className="tile">
        <div className="tile-head">
          <span className="tile-title">{title}</span>
          <span className="tag simulated">Simulated</span>
        </div>

        <div className="tile-value">
          {formatNumber(dp.world_b)}
          <span className="tile-unit">{delta.unit}</span>
        </div>

        <div className="tile-band">
          World A {formatNumber(dp.world_a)} → B {formatNumber(dp.world_b)}
        </div>

        <Sparkline points={effectPts} index={i} color={color} />
        <div className="tile-band">
          Δ policy effect · band {formatNumber(dp.low)}–{formatNumber(dp.high)}
        </div>

        <div className="tile-deltas">
          <span className="delta">
            <span className="delta-label">vs baseline</span>
            <span className={`delta-val ${dp.delta === 0 ? "muted" : good ? "down" : "up"}`}>
              {formatNumber(dp.delta)}
              {deltaPct != null ? ` (${formatSignedPct(deltaPct / 100)})` : ""}
            </span>
          </span>
        </div>

        {canExplain && <EvidenceButton onClick={explain} />}
      </div>
    );
  }

  // --- No series at all: honest placeholder --------------------------------
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

  // --- Baseline mode -------------------------------------------------------
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

      {canExplain && <EvidenceButton onClick={explain} />}
    </div>
  );
}

/** "Trace the evidence" affordance — opens the causal provenance drawer (SPEC §26). */
function EvidenceButton({ onClick }: { onClick: () => void }) {
  return (
    <button type="button" className="tile-evidence" onClick={onClick}>
      Evidence ▸
    </button>
  );
}
