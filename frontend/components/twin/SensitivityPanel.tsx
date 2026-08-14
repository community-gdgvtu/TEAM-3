"use client";

/**
 * Global sensitivity tornado (SPEC §24/§26): turns the compiled policy into a
 * cross-metric one-at-a-time (OAT) attribution via `POST /sensitivity`. Each
 * documented assumption is swept from its plausible low to high edge (others
 * held at default) and the resulting swing in *every* headline metric's policy
 * effect Δ(B−A) is measured. The panel ranks which assumptions the whole
 * dashboard's answer rests on ("if you only pin two numbers, pin these") and,
 * per metric, draws a signed tornado of the assumption swings around the default
 * effect.
 *
 * Where the Uncertainty tab gives a Monte-Carlo fan for a *single* metric, this
 * gives the cheap, deterministic, cross-metric leverage map.
 *
 * Honesty (SPEC §24/§26/§34): every number is a re-run of the deterministic
 * World-A/B/Δ model at a documented assumption's edges — the LLM never touches
 * the numeric path. Bar length is *leverage, not likelihood*; interactions
 * between assumptions are not captured here (that is what the Uncertainty fan
 * does). The overridable set is the same one the Uncertainty engine sweeps, so
 * the two can never disagree. Idle / loading / error states are shown honestly
 * when the backend is down — a tornado is never fabricated.
 */

import { useEffect, useState } from "react";

import { runSensitivity } from "../../lib/api";
import type {
  AssumptionDriver,
  MetricTornado,
  SensitivityResult,
} from "../../lib/api";
import { formatNumber } from "../../lib/format";
import { useTwin } from "./TwinStore";

type Status = "idle" | "loading" | "ready" | "error";

/** Horizon options snap to the Time-Machine checkpoints (SPEC §27). */
const HORIZONS: Array<{ label: string; months: number }> = [
  { label: "Year 1", months: 12 },
  { label: "Year 2", months: 24 },
  { label: "Year 5", months: 60 },
  { label: "Year 10", months: 120 },
];

/** Signed value for display. */
function signed(v: number): string {
  return `${v > 0 ? "+" : ""}${formatNumber(v)}`;
}

export default function SensitivityPanel() {
  const { policy } = useTwin();
  const [status, setStatus] = useState<Status>("idle");
  const [result, setResult] = useState<SensitivityResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [horizon, setHorizon] = useState(60);

  // A fresh/edited policy invalidates any prior tornado.
  useEffect(() => {
    setResult(null);
    setStatus("idle");
    setError(null);
  }, [policy]);

  async function run() {
    if (!policy) return;
    setStatus("loading");
    setError(null);
    try {
      const r = await runSensitivity(policy, horizon);
      setResult(r);
      setStatus("ready");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Sensitivity model failed");
      setStatus("error");
    }
  }

  return (
    <section className="card sens">
      <div className="dashboard-head">
        <h2>Sensitivity tornado</h2>
        <span className="dashboard-sub">
          What does the answer rest on? · one-at-a-time leverage across every
          metric (SPEC §24/§26)
        </span>
      </div>

      {!policy ? (
        <div className="waiting">
          <span className="tag muted">No policy yet</span>
          <p>
            Compile a policy above to sweep each documented assumption across its
            plausible range and rank which ones the whole dashboard&rsquo;s answer
            depends on.
          </p>
        </div>
      ) : (
        <>
          <div className="run-actions">
            <label className="run-horizon">
              <span className="run-label">Tornado horizon</span>
              <select
                value={horizon}
                onChange={(e) => setHorizon(Number(e.target.value))}
              >
                {HORIZONS.map((h) => (
                  <option key={h.months} value={h.months}>
                    {h.label}
                  </option>
                ))}
              </select>
            </label>
            <button
              type="button"
              className="btn primary"
              onClick={run}
              disabled={status === "loading"}
            >
              {status === "loading"
                ? "Sweeping…"
                : result
                  ? "Re-run"
                  : "Run tornado"}
            </button>
            {result && <span className="tag estimated">Estimated</span>}
          </div>

          <p className="hint sens-consistency">
            Deterministic re-runs of the same World-A/B/Δ model at documented
            assumption edges — no LLM on the numeric path. Bar length =
            <strong> leverage, not likelihood</strong>; assumption interactions
            are not captured here (that is the Uncertainty fan). Same overridable
            set the Uncertainty tab sweeps, so the two can&rsquo;t disagree.
          </p>

          {status === "error" && <p className="hint error-text">{error}</p>}

          {result && status !== "loading" && <TornadoResult r={result} />}
        </>
      )}
    </section>
  );
}

function TornadoResult({ r }: { r: SensitivityResult }) {
  return (
    <div className="sens-body">
      <p className="sens-headline">{r.headline}</p>
      <p className="sens-meta">
        Horizon {r.horizon.label} · policy {r.policy_id} ·{" "}
        {r.swept_assumptions.length} assumptions swept ·{" "}
        {r.tornados.length} metrics
      </p>

      {r.drivers.length > 0 && (
        <>
          <h3 className="sens-sub">What the answer rests on</h3>
          <p className="sens-sub-note">
            Assumptions ranked by aggregate leverage across the whole dashboard
            (mean share of each metric&rsquo;s total sensitivity).
          </p>
          <Drivers drivers={r.drivers} />
        </>
      )}

      <h3 className="sens-sub">Per-metric tornados</h3>
      <p className="sens-sub-note">
        Each bar spans the metric&rsquo;s policy effect Δ(B−A) with one assumption
        at its low vs high edge; the marker is the default-assumption effect.
      </p>
      <div className="sens-tornados">
        {r.tornados.map((t) => (
          <MetricTornadoCard key={t.key} t={t} />
        ))}
      </div>

      {r.not_modelled.length > 0 && (
        <details className="sens-notmodelled">
          <summary>Scope limits of this analysis ({r.not_modelled.length})</summary>
          <ul>
            {r.not_modelled.map((n, i) => (
              <li key={i}>{n}</li>
            ))}
          </ul>
        </details>
      )}

      <p className="hint sens-note">{r.note}</p>
    </div>
  );
}

/** Aggregate leverage ranking — a horizontal share bar per assumption. */
function Drivers({ drivers }: { drivers: AssumptionDriver[] }) {
  const maxScore = Math.max(1e-9, ...drivers.map((d) => d.global_score));
  return (
    <div className="sens-drivers">
      {drivers.map((d, i) => {
        const pct = (d.global_score / maxScore) * 100;
        return (
          <div
            className={`sens-driver${d.matters ? "" : " flat"}`}
            key={d.name}
            title={d.note}
          >
            <span className="sens-driver-rank">{i + 1}</span>
            <span className="sens-driver-label">
              {d.label}
              {d.unit ? <span className="sens-driver-unit"> ({d.unit})</span> : null}
              {!d.matters && (
                <span className="tag muted sens-flat-tag">no effect here</span>
              )}
            </span>
            <div className="sens-driver-track">
              <div
                className="sens-driver-bar"
                style={{ width: `${d.matters ? Math.max(pct, 1.5) : 0}%` }}
              />
            </div>
            <span className="sens-driver-score">
              {(d.global_score * 100).toFixed(0)}%
              {d.max_pct_of_default != null && d.matters
                ? ` · ≤${Math.round(d.max_pct_of_default)}% of Δ`
                : ""}
            </span>
          </div>
        );
      })}
    </div>
  );
}

/** One headline metric's tornado card. */
function MetricTornadoCard({ t }: { t: MetricTornado }) {
  // Symmetric x-range spanning every bar edge and the default effect, around 0.
  const extents: number[] = [0, t.default_delta];
  for (const b of t.bars) extents.push(b.delta_at_low, b.delta_at_high);
  const bound = Math.max(1e-9, ...extents.map((v) => Math.abs(v)));
  // Map a value in [-bound, bound] → [0, 100]% of the track.
  const xf = (v: number) => 50 + (v / bound) * 48;

  const bars = t.bars.filter((b) => b.direction !== "flat");
  const flatCount = t.bars.length - bars.length;

  return (
    <div className="sens-metric">
      <div className="sens-metric-head">
        <span className="sens-metric-label">
          {t.label}
          {t.unit ? <span className="sens-metric-unit"> ({t.unit})</span> : null}
        </span>
        <span className={`tag ${t.tag.toLowerCase()}`}>{t.tag}</span>
      </div>
      <div className="sens-metric-default">
        Default effect Δ(B−A): <strong>{signed(t.default_delta)}</strong>
        {t.most_influential && (
          <>
            {" · "}most sensitive to{" "}
            <strong>
              {t.bars.find((b) => b.name === t.most_influential)?.label ??
                t.most_influential}
            </strong>
          </>
        )}
      </div>

      {bars.length === 0 ? (
        <p className="hint">
          No assumption moves this metric&rsquo;s effect for this policy.
        </p>
      ) : (
        <div className="sens-tor">
          {bars.map((b) => {
            const a = xf(b.delta_at_low);
            const c = xf(b.delta_at_high);
            const left = Math.min(a, c);
            const width = Math.max(Math.abs(c - a), 0.6);
            return (
              <div className="sens-tor-row" key={b.name}>
                <span
                  className="sens-tor-label"
                  title={`${b.name}: ${formatNumber(b.low_value)}…${formatNumber(
                    b.high_value,
                  )}${b.unit ? " " + b.unit : ""}`}
                >
                  {b.label}
                </span>
                <div className="sens-tor-track">
                  <div className="sens-tor-mid" />
                  <div
                    className={`sens-tor-bar ${b.direction}`}
                    style={{ left: `${left}%`, width: `${width}%` }}
                  />
                  <div
                    className="sens-tor-default"
                    style={{ left: `${xf(t.default_delta)}%` }}
                    title={`default Δ ${signed(t.default_delta)}`}
                  />
                </div>
                <span
                  className="sens-tor-swing"
                  title="metric Δ moves this much low→high"
                >
                  {signed(b.swing)}
                  {b.pct_of_default != null
                    ? ` · ${Math.round(b.pct_of_default)}%`
                    : ""}
                </span>
              </div>
            );
          })}
        </div>
      )}
      {flatCount > 0 && (
        <p className="sens-flat-note">
          {flatCount} assumption{flatCount === 1 ? "" : "s"} flat on this metric.
        </p>
      )}
    </div>
  );
}
