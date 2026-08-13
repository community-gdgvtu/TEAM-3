"use client";

/**
 * Ensemble forecast view (SPEC §8): the flagship cordon-traffic effect estimated
 * by three independent methods — structural agent-based, historical-analogue
 * transfer, and reduced-form elasticity — pooled with documented weights via
 * `POST /ensemble`.
 *
 * The honesty story this panel exists to tell (SPEC §8/§34): the headline band is
 * NOT one model's noise, it spans how much the *methods disagree*. A wide band
 * means the methods genuinely diverge, not false precision. Each method shows its
 * own central estimate + range, its ensemble weight, and whether it even applies
 * to this intervention. No LLM touches any number. When the backend is down the
 * panel shows an honest waiting/error state rather than inventing a forecast.
 */

import { useEffect, useState } from "react";

import { runEnsemble } from "../../lib/api";
import type { EnsembleForecast, EnsembleMetric, MethodEstimate } from "../../lib/api";
import { useTwin } from "./TwinStore";

type Status = "idle" | "loading" | "ready" | "error";

/** Signed percentage, e.g. -30 → "−30.0%". */
function pct(v: number): string {
  const s = v > 0 ? "+" : v < 0 ? "−" : "";
  return `${s}${Math.abs(v).toFixed(1)}%`;
}

const DISAGREE_LABEL: Record<string, string> = {
  low: "methods agree",
  moderate: "some disagreement",
  high: "methods disagree",
};

export default function EnsemblePanel() {
  const { policy } = useTwin();
  const [status, setStatus] = useState<Status>("idle");
  const [forecast, setForecast] = useState<EnsembleForecast | null>(null);
  const [error, setError] = useState<string | null>(null);

  // A fresh/edited policy invalidates any prior ensemble run.
  useEffect(() => {
    setForecast(null);
    setStatus("idle");
    setError(null);
  }, [policy]);

  async function run() {
    if (!policy) return;
    setStatus("loading");
    setError(null);
    try {
      const f = await runEnsemble(policy);
      setForecast(f);
      setStatus("ready");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Ensemble model failed");
      setStatus("error");
    }
  }

  return (
    <section className="card ensemble">
      <div className="dashboard-head">
        <h2>Ensemble forecast</h2>
        <span className="dashboard-sub">
          Flagship cordon effect · 3 independent methods, band = disagreement (SPEC §8)
        </span>
      </div>

      {!policy ? (
        <div className="waiting">
          <span className="tag muted">No policy yet</span>
          <p>
            Compile a policy above to estimate its headline effect with three
            independent forecasting methods and see how much they agree.
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
                ? "Pooling methods…"
                : forecast
                  ? "Re-run ensemble"
                  : "Run ensemble"}
            </button>
            {forecast && <span className="tag estimated">Estimated (cross-method)</span>}
          </div>

          {status === "error" && (
            <p className="hint error-text">Couldn&rsquo;t run ensemble: {error}</p>
          )}

          {status === "idle" && !forecast && (
            <p className="hint">
              Pools an agent-based model, a historical-analogue transfer, and a
              reduced-form elasticity into one banded estimate for the cordon
              effect. Click to run.
            </p>
          )}

          {forecast && status !== "loading" && (
            <div className="ens-body">
              {forecast.metrics.map((m) => (
                <EnsembleMetricBlock key={m.metric_key} m={m} />
              ))}
              <p className="hint ens-note">{forecast.note}</p>
            </div>
          )}
        </>
      )}
    </section>
  );
}

function EnsembleMetricBlock({ m }: { m: EnsembleMetric }) {
  const applicable = m.methods.filter((x) => x.applicable);
  // Shared linear scale across every method range AND the ensemble band, padded
  // a touch so end markers aren't clipped. Guard the degenerate zero-width case.
  const lows = [...m.methods.map((x) => x.low_pct), m.ensemble_low_pct];
  const highs = [...m.methods.map((x) => x.high_pct), m.ensemble_high_pct];
  let lo = Math.min(...lows, 0);
  let hi = Math.max(...highs, 0);
  if (hi - lo < 1e-6) {
    lo -= 1;
    hi += 1;
  }
  const pad = (hi - lo) * 0.06;
  lo -= pad;
  hi += pad;
  const span = hi - lo;
  const xf = (v: number) => ((v - lo) / span) * 100;

  const disagreeClass =
    m.disagreement === "high"
      ? "warn"
      : m.disagreement === "low"
        ? "good"
        : "mid";

  return (
    <div className="ens-metric">
      <div className="ens-head">
        <div className="ens-headline">
          <span className="ens-central">{pct(m.ensemble_central_pct)}</span>
          <span className="ens-label">{m.label}</span>
        </div>
        <div className="ens-head-meta">
          <span className="ens-band">
            band {pct(m.ensemble_low_pct)} … {pct(m.ensemble_high_pct)}
          </span>
          <span className={`ens-disagree ${disagreeClass}`}>
            {DISAGREE_LABEL[m.disagreement] ?? m.disagreement} · spread{" "}
            {m.method_spread_pct.toFixed(1)} pts
          </span>
          <span className={`tag ${m.tag.toLowerCase()}`}>{m.tag}</span>
        </div>
      </div>

      {m.interpretation && <p className="ens-interp">{m.interpretation}</p>}

      {/* Range chart: one row per method (central marker + own range), with the
          pooled ensemble band drawn as a highlighted vertical span behind them. */}
      <div
        className="ens-chart"
        role="img"
        aria-label={`Method estimates for ${m.label}; ensemble central ${pct(
          m.ensemble_central_pct,
        )}, band ${pct(m.ensemble_low_pct)} to ${pct(m.ensemble_high_pct)}.`}
      >
        <div className="ens-scale">
          <span>{pct(lo)}</span>
          {lo < 0 && hi > 0 && (
            <span
              className="ens-zero-label"
              style={{ left: `${xf(0)}%` }}
            >
              0
            </span>
          )}
          <span>{pct(hi)}</span>
        </div>

        <div className="ens-plot">
          {/* ensemble band + central line */}
          <div
            className="ens-eband"
            style={{
              left: `${xf(m.ensemble_low_pct)}%`,
              width: `${Math.max(xf(m.ensemble_high_pct) - xf(m.ensemble_low_pct), 0.5)}%`,
            }}
            title={`Ensemble band ${pct(m.ensemble_low_pct)} … ${pct(m.ensemble_high_pct)}`}
          />
          <div className="ens-ecentral" style={{ left: `${xf(m.ensemble_central_pct)}%` }} />
          {lo < 0 && hi > 0 && (
            <div className="ens-zeroline" style={{ left: `${xf(0)}%` }} />
          )}

          {m.methods.map((x, i) => (
            <MethodRow key={x.method_id} x={x} xf={xf} rowIndex={i} rows={m.methods.length} />
          ))}
        </div>
      </div>

      {/* Legend / detail: one card per method with weight + range + assumptions. */}
      <div className="ens-methods">
        {m.methods.map((x) => (
          <MethodCard key={x.method_id} x={x} />
        ))}
      </div>

      {applicable.length < m.methods.length && (
        <p className="hint ens-inapplicable">
          {m.methods.length - applicable.length} method(s) don&rsquo;t fit this
          intervention and were down-weighted to zero — shown greyed, not dropped.
        </p>
      )}
    </div>
  );
}

function MethodRow({
  x,
  xf,
  rowIndex,
  rows,
}: {
  x: MethodEstimate;
  xf: (v: number) => number;
  rowIndex: number;
  rows: number;
}) {
  // Stagger rows vertically inside the plot so overlapping ranges stay readable.
  const top = rows > 1 ? 12 + (rowIndex * 64) / rows : 40;
  const left = xf(x.low_pct);
  const width = Math.max(xf(x.high_pct) - xf(x.low_pct), 0.4);
  return (
    <div
      className={`ens-mrow${x.applicable ? "" : " off"}`}
      style={{ top: `${top}%` }}
      title={`${x.name}: ${x.central_pct.toFixed(1)}% (range ${x.low_pct.toFixed(
        1,
      )} … ${x.high_pct.toFixed(1)})`}
    >
      <div className="ens-mrange" style={{ left: `${left}%`, width: `${width}%` }} />
      <div className="ens-mcentral" style={{ left: `${xf(x.central_pct)}%` }} />
    </div>
  );
}

function MethodCard({ x }: { x: MethodEstimate }) {
  return (
    <div className={`ens-mcard${x.applicable ? "" : " off"}`}>
      <div className="ens-mcard-head">
        <span className="ens-mname">{x.name}</span>
        <span className="ens-mweight" title="Ensemble weight">
          w {(x.weight * 100).toFixed(0)}%
        </span>
      </div>
      <div className="ens-mstat">
        <span className="ens-mcentral-val">{pct(x.central_pct)}</span>
        <span className="ens-mrange-val">
          {pct(x.low_pct)} … {pct(x.high_pct)}
        </span>
        <span className={`tag ${x.tag.toLowerCase()}`}>{x.tag}</span>
      </div>
      <p className="ens-mapproach">
        <span className="ens-mlayer">{x.spec_layer}</span> · {x.approach}
      </p>
      {!x.applicable && (
        <p className="ens-moff-note">Not applicable to this intervention (weight 0).</p>
      )}
      {x.note && <p className="ens-mnote">{x.note}</p>}
    </div>
  );
}
