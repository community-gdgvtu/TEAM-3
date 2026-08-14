"use client";

/**
 * Uncertainty fan view (SPEC §24): turns one metric of the compiled policy into a
 * fan of plausible futures via `POST /uncertainty` — a Monte-Carlo sweep over the
 * uncertain input assumptions gives a median trajectory with nested 50/80/95%
 * intervals at every horizon, a ranked one-at-a-time sensitivity list, and a
 * behavioural-regime ensemble measuring model disagreement.
 *
 * Honesty (SPEC §24/§34): every number is a re-run of the deterministic structural
 * model with perturbed *assumptions* — the LLM never touches the numeric path. The
 * fan makes uncertainty visible rather than quoting a false-precision point. If the
 * chosen metric key isn't in the model's delta series, the backend returns the
 * valid keys and we render them as one-click chips instead of guessing.
 */

import { useEffect, useState } from "react";

import { MetricNotFoundError, runUncertainty } from "../../lib/api";
import type {
  HorizonBand,
  SensitivityEntry,
  UncertaintyResult,
} from "../../lib/api";
import { formatNumber } from "../../lib/format";
import { useTwin } from "./TwinStore";

type Status = "idle" | "loading" | "ready" | "error";

const DEFAULT_METRIC = "traffic.daily_vehicle_km";

/** Signed value for display. */
function signed(v: number): string {
  return `${v > 0 ? "+" : ""}${formatNumber(v)}`;
}

export default function UncertaintyPanel() {
  const { policy } = useTwin();
  const [status, setStatus] = useState<Status>("idle");
  const [result, setResult] = useState<UncertaintyResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [available, setAvailable] = useState<string[] | null>(null);
  const [metricKey, setMetricKey] = useState(DEFAULT_METRIC);

  // A fresh/edited policy invalidates any prior fan.
  useEffect(() => {
    setResult(null);
    setStatus("idle");
    setError(null);
    setAvailable(null);
  }, [policy]);

  async function run(key: string) {
    if (!policy) return;
    setMetricKey(key);
    setStatus("loading");
    setError(null);
    setAvailable(null);
    try {
      const r = await runUncertainty(policy, key);
      setResult(r);
      setStatus("ready");
    } catch (e: unknown) {
      if (e instanceof MetricNotFoundError) {
        setError(`No metric "${key}" in this run — pick one of the model's metrics below.`);
        setAvailable(e.available);
      } else {
        setError(e instanceof Error ? e.message : "Uncertainty model failed");
      }
      setStatus("error");
    }
  }

  return (
    <section className="card uncertainty">
      <div className="dashboard-head">
        <h2>Uncertainty fan</h2>
        <span className="dashboard-sub">
          Monte-Carlo fan of futures · median + 50/80/95% bands (SPEC §24)
        </span>
      </div>

      {!policy ? (
        <div className="waiting">
          <span className="tag muted">No policy yet</span>
          <p>
            Compile a policy above to sweep its uncertain assumptions and see the
            fan of plausible futures for a chosen metric.
          </p>
        </div>
      ) : (
        <>
          <div className="unc-controls">
            <label className="unc-metric-label" htmlFor="unc-metric">
              Metric
            </label>
            <input
              id="unc-metric"
              className="unc-metric-input"
              value={metricKey}
              onChange={(e) => setMetricKey(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") run(metricKey);
              }}
              spellCheck={false}
            />
            <button
              type="button"
              className="btn primary"
              onClick={() => run(metricKey)}
              disabled={status === "loading"}
            >
              {status === "loading" ? "Sweeping…" : result ? "Re-run" : "Run sweep"}
            </button>
            {result && <span className="tag simulated">Simulated</span>}
          </div>

          {status === "error" && (
            <p className="hint error-text">{error}</p>
          )}

          {available && available.length > 0 && (
            <div className="unc-available">
              {available.map((k) => (
                <button
                  key={k}
                  type="button"
                  className="unc-key-chip"
                  onClick={() => run(k)}
                >
                  {k}
                </button>
              ))}
            </div>
          )}

          {result && status !== "loading" && <FanResult r={result} />}
        </>
      )}
    </section>
  );
}

function FanResult({ r }: { r: UncertaintyResult }) {
  return (
    <div className="unc-body">
      <div className="unc-summary">
        <div className="unc-headline">
          <span className="unc-median">{signed(r.median)}</span>
          <span className="unc-metric-name">
            {r.metric_label}
            {r.unit ? ` (${r.unit})` : ""} · median Δ @ {r.horizon.label}
          </span>
        </div>
        <div className="unc-intervals">
          {r.intervals.map((iv) => (
            <span className="unc-iv" key={iv.level}>
              {iv.level}%: {signed(iv.low)} … {signed(iv.high)}
            </span>
          ))}
        </div>
        <p className="unc-point">
          Deterministic point estimate: <strong>{signed(r.point_estimate)}</strong> ·{" "}
          {r.samples} Monte-Carlo samples · seed {r.seed} (reproducible)
        </p>
      </div>

      <FanChart fan={r.fan} unit={r.unit} />

      {r.influential_assumptions.length > 0 && (
        <>
          <h3 className="unc-sub">Most-influential assumptions</h3>
          <p className="unc-sub-note">
            One-at-a-time swing of the metric Δ as each assumption spans its plausible range.
          </p>
          <Tornado entries={r.influential_assumptions} />
        </>
      )}

      {r.model_disagreement.variants.length > 0 && (
        <>
          <h3 className="unc-sub">
            Behavioural-regime disagreement
            <span className="unc-spread" title="max Δ − min Δ across regimes">
              spread {formatNumber(r.model_disagreement.spread)}
            </span>
          </h3>
          <div className="unc-regimes">
            {r.model_disagreement.variants.map((v) => (
              <div className="unc-regime" key={v.name} title={v.description}>
                <span className="unc-regime-label">{v.label}</span>
                <span className="unc-regime-delta">{signed(v.delta)}</span>
              </div>
            ))}
          </div>
          <p className="hint">{r.model_disagreement.note}</p>
        </>
      )}

      {r.swept_assumptions.length > 0 && (
        <p className="unc-swept">
          Swept assumptions: {r.swept_assumptions.join(", ")}
        </p>
      )}

      <p className="hint unc-note">{r.note}</p>
    </div>
  );
}

/** SVG fan: nested 95/80/50% bands (light→dark) + a median line, across horizons. */
function FanChart({ fan, unit }: { fan: HorizonBand[]; unit: string }) {
  if (fan.length < 2) {
    return <p className="hint">Not enough checkpoints to draw a fan.</p>;
  }
  const W = 720;
  const H = 240;
  const padL = 52;
  const padR = 16;
  const padT = 14;
  const padB = 28;

  const months = fan.map((b) => b.t_months);
  const xMin = Math.min(...months);
  const xMax = Math.max(...months);
  const xSpan = xMax - xMin || 1;

  // Y range spans the widest band (95%) plus the median, padded, and always 0.
  const allVals: number[] = [0];
  for (const b of fan) {
    allVals.push(b.median);
    for (const iv of b.intervals) {
      allVals.push(iv.low, iv.high);
    }
  }
  let yMin = Math.min(...allVals);
  let yMax = Math.max(...allVals);
  if (yMax - yMin < 1e-6) {
    yMin -= 1;
    yMax += 1;
  }
  const yPad = (yMax - yMin) * 0.08;
  yMin -= yPad;
  yMax += yPad;

  const xf = (m: number) => padL + ((m - xMin) / xSpan) * (W - padL - padR);
  const yf = (v: number) => padT + (1 - (v - yMin) / (yMax - yMin)) * (H - padT - padB);

  // Draw the widest interval first so narrower ones layer on top.
  const levels = [95, 80, 50];
  const bandFill: Record<number, string> = {
    95: "rgba(79,140,255,0.14)",
    80: "rgba(79,140,255,0.22)",
    50: "rgba(79,140,255,0.34)",
  };

  function bandPath(level: number): string | null {
    const tops: string[] = [];
    const bottoms: string[] = [];
    for (const b of fan) {
      const iv = b.intervals.find((i) => i.level === level);
      if (!iv) return null;
      tops.push(`${xf(b.t_months).toFixed(1)},${yf(iv.high).toFixed(1)}`);
      bottoms.push(`${xf(b.t_months).toFixed(1)},${yf(iv.low).toFixed(1)}`);
    }
    bottoms.reverse();
    return `M${tops.join(" L")} L${bottoms.join(" L")} Z`;
  }

  const medianLine = fan
    .map((b) => `${xf(b.t_months).toFixed(1)},${yf(b.median).toFixed(1)}`)
    .join(" ");

  const zeroY = yMin <= 0 && yMax >= 0 ? yf(0) : null;

  return (
    <div className="unc-chart">
      <svg
        viewBox={`0 0 ${W} ${H}`}
        role="img"
        aria-label={`Uncertainty fan across ${fan.length} horizons: nested 50/80/95% intervals around the median.`}
        preserveAspectRatio="xMidYMid meet"
      >
        {/* y gridlines: min, 0, max */}
        <line x1={padL} y1={yf(yMax)} x2={W - padR} y2={yf(yMax)} className="unc-grid" />
        <line x1={padL} y1={yf(yMin)} x2={W - padR} y2={yf(yMin)} className="unc-grid" />
        <text x={4} y={yf(yMax) + 4} className="unc-axis">
          {formatNumber(yMax)}
        </text>
        <text x={4} y={yf(yMin) + 4} className="unc-axis">
          {formatNumber(yMin)}
        </text>
        {zeroY != null && (
          <>
            <line x1={padL} y1={zeroY} x2={W - padR} y2={zeroY} className="unc-zero" />
            <text x={4} y={zeroY + 4} className="unc-axis">
              0
            </text>
          </>
        )}

        {levels.map((lv) => {
          const d = bandPath(lv);
          return d ? <path key={lv} d={d} fill={bandFill[lv]} stroke="none" /> : null;
        })}

        <polyline points={medianLine} className="unc-median-line" fill="none" />

        {/* x labels: first, middle, last */}
        {[fan[0], fan[Math.floor(fan.length / 2)], fan[fan.length - 1]].map((b, i) => (
          <text
            key={i}
            x={xf(b.t_months)}
            y={H - 8}
            className="unc-axis"
            textAnchor={i === 0 ? "start" : i === 2 ? "end" : "middle"}
          >
            {b.t_years}y
          </text>
        ))}
      </svg>
      <div className="unc-legend">
        <span className="unc-leg median">median</span>
        <span className="unc-leg b50">50%</span>
        <span className="unc-leg b80">80%</span>
        <span className="unc-leg b95">95%</span>
        {unit && <span className="unc-leg-unit">Δ in {unit}</span>}
      </div>
    </div>
  );
}

/** Sensitivity tornado — bars from delta_at_low to delta_at_high, ranked. */
function Tornado({ entries }: { entries: SensitivityEntry[] }) {
  const maxSwing = Math.max(
    1,
    ...entries.flatMap((e) => [Math.abs(e.delta_at_low), Math.abs(e.delta_at_high)]),
  );
  const scale = (v: number) => 50 + (v / maxSwing) * 48; // percent, centered at 50
  return (
    <div className="unc-tornado">
      {entries.map((e) => {
        const a = scale(e.delta_at_low);
        const b = scale(e.delta_at_high);
        const left = Math.min(a, b);
        const width = Math.max(Math.abs(b - a), 0.5);
        return (
          <div className="unc-tor-row" key={e.name}>
            <span className="unc-tor-label" title={`${e.name} (${e.low_value}…${e.high_value}${e.unit ? " " + e.unit : ""})`}>
              {e.label}
            </span>
            <div className="unc-tor-track">
              <div className="unc-tor-mid" />
              <div className="unc-tor-bar" style={{ left: `${left}%`, width: `${width}%` }} />
            </div>
            <span className="unc-tor-swing" title="influence magnitude">
              ±{formatNumber(e.swing / 2)}
              {e.swing_pct_of_median != null ? ` · ${Math.round(e.swing_pct_of_median)}%` : ""}
            </span>
          </div>
        );
      })}
    </div>
  );
}
