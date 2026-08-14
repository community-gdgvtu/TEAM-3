"use client";

/**
 * Time-series forecast view (SPEC §7.2): turns the compiled policy into a fitted
 * structural forecast of the city. For each headline metric the backend fits
 * **World A** first — a local-linear-trend + 12-month seasonal + AR(1) model over
 * a seeded synthetic monthly history anchored to the ABM baseline — with
 * prediction intervals that *widen with horizon* because their variance is
 * derived from the fit; the deterministic ABM policy Δ(B−A) then alters that
 * baseline trajectory to give **World B**.
 *
 * The honesty story this panel tells (SPEC §7.2/§8/§34): the synthetic history is
 * Simulated (the city keeps no real logs), the statistical baseline forecast is
 * Estimated, and the policy shift is Simulated — three provenance classes on one
 * chart, all surfaced. No LLM touches any number. The bands are the model's own
 * uncertainty, not decoration, and they visibly grow toward year 10. The fit is
 * made auditable (slope, seasonality, AR(1), in-sample + honest held-out MAPE)
 * and the layer states plainly what it does *not* model. When the backend is down
 * the panel shows an honest waiting/error state, never a fabricated trajectory.
 */

import { useEffect, useMemo, useState } from "react";

import { runTimeseries } from "../../lib/api";
import type {
  ForecastPoint,
  MetricForecast,
  TimeSeriesForecast,
} from "../../lib/api";
import { formatNumber } from "../../lib/format";
import { useTwin } from "./TwinStore";

type Status = "idle" | "loading" | "ready" | "error";

/** Signed percentage, e.g. -12.3 → "−12.3%". */
function pct(v: number, dp = 1): string {
  const s = v > 0 ? "+" : v < 0 ? "−" : "";
  return `${s}${Math.abs(v).toFixed(dp)}%`;
}

/** Signed absolute value for display. */
function signed(v: number): string {
  return `${v > 0 ? "+" : ""}${formatNumber(v)}`;
}

export default function TimeseriesPanel() {
  const { policy } = useTwin();
  const [status, setStatus] = useState<Status>("idle");
  const [result, setResult] = useState<TimeSeriesForecast | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [metricKey, setMetricKey] = useState<string | null>(null);
  const [showAssumptions, setShowAssumptions] = useState(false);

  // A fresh/edited policy invalidates any prior forecast.
  useEffect(() => {
    setResult(null);
    setStatus("idle");
    setError(null);
    setMetricKey(null);
  }, [policy]);

  async function run() {
    if (!policy) return;
    setStatus("loading");
    setError(null);
    try {
      const r = await runTimeseries(policy);
      setResult(r);
      setMetricKey(r.metrics[0]?.key ?? null);
      setStatus("ready");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Time-series layer failed");
      setStatus("error");
    }
  }

  const selected = useMemo(
    () => result?.metrics.find((m) => m.key === metricKey) ?? result?.metrics[0] ?? null,
    [result, metricKey],
  );

  return (
    <section className="card ts-panel">
      <div className="dashboard-head">
        <h2>Time-series forecast</h2>
        <span className="dashboard-sub">
          Fitted structural baseline (trend + seasonal + AR1), then policy alters it (SPEC §7.2)
        </span>
      </div>

      {!policy ? (
        <div className="waiting">
          <span className="tag muted">No policy yet</span>
          <p>
            Compile a policy above to fit a structural time-series model of the
            city&rsquo;s baseline (World A) and see how the policy shifts each
            headline metric&rsquo;s trajectory (World B) over ten years, with
            prediction bands that widen with the horizon.
          </p>
        </div>
      ) : (
        <>
          <div className="policy-actions" style={{ marginTop: 0 }}>
            <button
              type="button"
              className="btn primary"
              onClick={run}
              disabled={status === "loading"}
            >
              {status === "loading"
                ? "Fitting the baseline…"
                : result
                  ? "Re-run forecast"
                  : "Run time-series forecast"}
            </button>
            {result && (
              <span className="ts-provenance">
                <span className="tag simulated">History Simulated</span>
                <span className="tag estimated">World A Estimated</span>
                <span className="tag simulated">World B Simulated</span>
              </span>
            )}
          </div>

          {status === "error" && (
            <p className="hint error-text">
              Couldn&rsquo;t run the time-series layer: {error}
            </p>
          )}

          {status === "idle" && !result && (
            <p className="hint">
              Fits World A first — a local-linear-trend + 12-month seasonal + AR(1)
              model over a seeded synthetic history anchored to the ABM baseline —
              then applies the deterministic ABM policy Δ(B−A) to give World B. No
              LLM touches any number (SPEC §7.2/§8/§34).
            </p>
          )}

          {result && selected && status !== "loading" && (
            <ForecastBody
              result={result}
              selected={selected}
              metricKey={selected.key}
              onPick={setMetricKey}
              showAssumptions={showAssumptions}
              onToggleAssumptions={() => setShowAssumptions((s) => !s)}
            />
          )}
        </>
      )}
    </section>
  );
}

function ForecastBody({
  result,
  selected,
  metricKey,
  onPick,
  showAssumptions,
  onToggleAssumptions,
}: {
  result: TimeSeriesForecast;
  selected: MetricForecast;
  metricKey: string;
  onPick: (k: string) => void;
  showAssumptions: boolean;
  onToggleAssumptions: () => void;
}) {
  const wa = selected.world_a;
  const wb = selected.world_b;
  const lastA = wa[wa.length - 1];
  const lastB = wb[wb.length - 1];
  const lastShift = selected.policy_shift_pct[selected.policy_shift_pct.length - 1] ?? 0;
  const horizon = result.checkpoints[result.checkpoints.length - 1];

  return (
    <div className="ts-body">
      {/* Metric selector */}
      <div className="ts-metric-chips" role="tablist" aria-label="Forecast metric">
        {result.metrics.map((m) => (
          <button
            key={m.key}
            type="button"
            role="tab"
            aria-selected={m.key === metricKey}
            className={`ts-chip${m.key === metricKey ? " active" : ""}`}
            onClick={() => onPick(m.key)}
          >
            {m.label}
          </button>
        ))}
      </div>

      {/* Headline at the final horizon */}
      {lastA && lastB && (
        <div className="ts-headline">
          <div className="ts-head-cell">
            <span className="ts-head-label">
              World A (baseline) @ {horizon?.label ?? "final"}
            </span>
            <span className="ts-head-val">
              {formatNumber(lastA.value)}
              {selected.unit ? ` ${selected.unit}` : ""}
            </span>
            <span className="ts-head-band">
              80%: {formatNumber(lastA.low80)} … {formatNumber(lastA.high80)}
            </span>
          </div>
          <div className="ts-head-cell">
            <span className="ts-head-label">World B (policy)</span>
            <span className="ts-head-val ts-b">
              {formatNumber(lastB.value)}
              {selected.unit ? ` ${selected.unit}` : ""}
            </span>
            <span className="ts-head-band">
              80%: {formatNumber(lastB.low80)} … {formatNumber(lastB.high80)}
            </span>
          </div>
          <div className="ts-head-cell">
            <span className="ts-head-label">Policy shift Δ(B−A)</span>
            <span className={`ts-head-val ${lastShift < 0 ? "ts-down" : lastShift > 0 ? "ts-up" : ""}`}>
              {pct(lastShift)}
            </span>
            <span className="ts-head-band">
              <span className="tag simulated">Simulated (ABM Δ)</span>
            </span>
          </div>
        </div>
      )}

      <ForecastChart metric={selected} />

      <div className="ts-chart-legend">
        <span className="ts-leg ts-leg-hist">synthetic history</span>
        <span className="ts-leg ts-leg-a">World A forecast</span>
        <span className="ts-leg ts-leg-b">World B (policy)</span>
        <span className="ts-leg-note">shaded = 80% / 95% prediction bands (widen with horizon)</span>
      </div>

      {/* Fit diagnostics — the model made auditable */}
      <h3 className="ts-sub">Fitted model (World A) — auditable</h3>
      <div className="ts-fit-grid">
        <FitCell label="Level (last obs.)" value={formatNumber(selected.fit.level)} />
        <FitCell label="Trend / month" value={signed(selected.fit.slope_per_month)} />
        <FitCell label="Seasonal amplitude" value={formatNumber(selected.fit.seasonal_amplitude)} />
        <FitCell label="AR(1) φ" value={selected.fit.ar1_phi.toFixed(3)} />
        <FitCell label="Residual σ" value={formatNumber(selected.fit.residual_sigma)} />
        <FitCell label="In-sample MAPE" value={`${selected.fit.in_sample_mape_pct.toFixed(2)}%`} />
        <FitCell
          label="Held-out MAPE"
          value={
            selected.fit.holdout_mape_pct != null
              ? `${selected.fit.holdout_mape_pct.toFixed(2)}%`
              : "—"
          }
          title="Honest out-of-sample backtest on a held-out tail; — when the series is too short."
        />
      </div>
      <p className="hint ts-method">{selected.fit.method}</p>

      {/* Per-checkpoint policy shift */}
      <h3 className="ts-sub">Policy shift by horizon <span className="tag simulated">Simulated</span></h3>
      <div className="ts-shift-row">
        {result.checkpoints.map((cp, i) => (
          <div className="ts-shift-cell" key={cp.t_months}>
            <span className="ts-shift-h">{cp.t_years}y</span>
            <span
              className={`ts-shift-v ${
                (selected.policy_shift_pct[i] ?? 0) < 0
                  ? "ts-down"
                  : (selected.policy_shift_pct[i] ?? 0) > 0
                    ? "ts-up"
                    : ""
              }`}
            >
              {pct(selected.policy_shift_pct[i] ?? 0)}
            </span>
          </div>
        ))}
      </div>

      {/* Assumptions + scope limits */}
      <div className="ts-foot">
        <button type="button" className="ts-toggle" onClick={onToggleAssumptions}>
          {showAssumptions ? "▾" : "▸"} Model assumptions ({Object.keys(result.assumptions).length})
        </button>
        {showAssumptions && (
          <table className="ts-assum-table">
            <tbody>
              {Object.entries(result.assumptions).map(([k, v]) => (
                <tr key={k}>
                  <td className="ts-assum-k">{k}</td>
                  <td className="ts-assum-v">{String(v)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {result.not_modelled.length > 0 && (
        <div className="ts-notmodelled">
          <span className="ts-nm-title">Not modelled here</span>
          <ul>
            {result.not_modelled.map((n, i) => (
              <li key={i}>{n}</li>
            ))}
          </ul>
        </div>
      )}

      <p className="hint ts-note">{result.note}</p>
    </div>
  );
}

function FitCell({ label, value, title }: { label: string; value: string; title?: string }) {
  return (
    <div className="ts-fit-cell" title={title}>
      <span className="ts-fit-label">{label}</span>
      <span className="ts-fit-val">{value}</span>
    </div>
  );
}

/**
 * SVG chart: synthetic monthly history (muted line, negative x), then the World A
 * and World B forecasts each drawn as nested 95%/80% prediction bands + a central
 * line across the checkpoints. The bands visibly widen toward year 10 — the whole
 * point of the layer (SPEC §7.2/§8).
 */
function ForecastChart({ metric }: { metric: MetricForecast }) {
  const wa = metric.world_a;
  const wb = metric.world_b;
  if (wa.length < 2) {
    return <p className="hint">Not enough checkpoints to draw a forecast.</p>;
  }

  const W = 760;
  const H = 280;
  const padL = 56;
  const padR = 16;
  const padT = 14;
  const padB = 30;

  const hist = metric.history;
  const histLen = hist.length;
  // History occupies negative months ending at 0; forecast runs 0..last checkpoint.
  const histX = (i: number) => -(histLen - 1 - i);
  const forecastMonths = wa.map((p) => p.t_months);
  const xMin = histLen > 0 ? histX(0) : Math.min(...forecastMonths);
  const xMax = Math.max(...forecastMonths);
  const xSpan = xMax - xMin || 1;

  // Y range spans history + both worlds' widest (95%) bands, padded, always incl. 0.
  const allVals: number[] = [0, ...hist];
  for (const p of [...wa, ...wb]) {
    allVals.push(p.value, p.low95, p.high95);
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
  const yf = (v: number) =>
    padT + (1 - (v - yMin) / (yMax - yMin)) * (H - padT - padB);

  function band(points: ForecastPoint[], lvl: 80 | 95): string {
    const lowKey = lvl === 80 ? "low80" : "low95";
    const highKey = lvl === 80 ? "high80" : "high95";
    const tops = points.map(
      (p) => `${xf(p.t_months).toFixed(1)},${yf(p[highKey]).toFixed(1)}`,
    );
    const bottoms = points
      .map((p) => `${xf(p.t_months).toFixed(1)},${yf(p[lowKey]).toFixed(1)}`)
      .reverse();
    return `M${tops.join(" L")} L${bottoms.join(" L")} Z`;
  }

  const lineOf = (points: ForecastPoint[]) =>
    points.map((p) => `${xf(p.t_months).toFixed(1)},${yf(p.value).toFixed(1)}`).join(" ");

  const histLine =
    histLen > 1
      ? hist.map((v, i) => `${xf(histX(i)).toFixed(1)},${yf(v).toFixed(1)}`).join(" ")
      : "";

  const zeroY = yMin <= 0 && yMax >= 0 ? yf(0) : null;
  const forecastStartX = xf(0);

  return (
    <div className="ts-chart">
      <svg
        viewBox={`0 0 ${W} ${H}`}
        role="img"
        aria-label={`Time-series forecast for ${metric.label}: synthetic history then World A (baseline) and World B (policy) forecasts with 80/95% prediction bands widening toward year 10.`}
        preserveAspectRatio="xMidYMid meet"
      >
        {/* y gridlines: max, min, 0 */}
        <line x1={padL} y1={yf(yMax)} x2={W - padR} y2={yf(yMax)} className="ts-grid" />
        <line x1={padL} y1={yf(yMin)} x2={W - padR} y2={yf(yMin)} className="ts-grid" />
        <text x={4} y={yf(yMax) + 4} className="ts-axis">
          {formatNumber(yMax)}
        </text>
        <text x={4} y={yf(yMin) + 4} className="ts-axis">
          {formatNumber(yMin)}
        </text>
        {zeroY != null && (
          <>
            <line x1={padL} y1={zeroY} x2={W - padR} y2={zeroY} className="ts-zero" />
            <text x={4} y={zeroY + 4} className="ts-axis">
              0
            </text>
          </>
        )}

        {/* "now" divider between history and forecast */}
        <line
          x1={forecastStartX}
          y1={padT}
          x2={forecastStartX}
          y2={H - padB}
          className="ts-now"
        />
        <text x={forecastStartX + 3} y={padT + 10} className="ts-axis ts-now-label">
          forecast →
        </text>

        {/* World A bands (blue), then World B bands (green) on top */}
        <path d={band(wa, 95)} className="ts-band-a95" />
        <path d={band(wa, 80)} className="ts-band-a80" />
        <path d={band(wb, 95)} className="ts-band-b95" />
        <path d={band(wb, 80)} className="ts-band-b80" />

        {/* History line */}
        {histLine && <polyline points={histLine} className="ts-hist-line" fill="none" />}

        {/* Central forecast lines */}
        <polyline points={lineOf(wa)} className="ts-line-a" fill="none" />
        <polyline points={lineOf(wb)} className="ts-line-b" fill="none" />

        {/* x labels */}
        {histLen > 1 && (
          <text x={xf(histX(0))} y={H - 8} className="ts-axis" textAnchor="start">
            −{Math.round((histLen - 1) / 12)}y
          </text>
        )}
        <text x={forecastStartX} y={H - 8} className="ts-axis" textAnchor="middle">
          now
        </text>
        <text x={xf(xMax)} y={H - 8} className="ts-axis" textAnchor="end">
          {Math.round(xMax / 12)}y
        </text>
      </svg>
    </div>
  );
}
