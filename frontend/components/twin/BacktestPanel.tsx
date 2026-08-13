"use client";

/**
 * Backtest scorecard view (SPEC §25): historical replay. The deterministic model
 * forecasts a known policy from pre-implementation state only, then `POST /backtest`
 * scores that forecast against the case's actuals — forecast error (MAE/RMSE/MAPE),
 * direction accuracy, interval calibration and event-timing error.
 *
 * This tab is policy-independent: it replays the engine's built-in benchmark case
 * (loaded from `GET /backtest/example`), so it works before the user compiles
 * anything. Honesty (SPEC §25/§34): the forecast is Simulated and the scores are
 * exact arithmetic, but the built-in case's ACTUALS are a synthetic benchmark, not
 * real observations — the panel stamps the actuals' provenance prominently so a
 * good score is never mistaken for validation against the real world.
 */

import { useEffect, useState } from "react";

import { getBacktestExample, runBacktest } from "../../lib/api";
import type { HistoricalCase, MetricScore, Scorecard } from "../../lib/api";
import { formatNumber } from "../../lib/format";

type Status = "idle" | "loading" | "ready" | "error";

export default function BacktestPanel() {
  const [benchmark, setBenchmark] = useState<HistoricalCase | null>(null);
  const [card, setCard] = useState<Scorecard | null>(null);
  const [status, setStatus] = useState<Status>("idle");
  const [error, setError] = useState<string | null>(null);

  // Load the built-in benchmark case description up front so the user sees what
  // is being replayed before they score it. Failure here is non-fatal.
  useEffect(() => {
    const ctrl = new AbortController();
    getBacktestExample(ctrl.signal)
      .then(setBenchmark)
      .catch(() => setBenchmark(null));
    return () => ctrl.abort();
  }, []);

  async function score() {
    setStatus("loading");
    setError(null);
    try {
      const c = await runBacktest(undefined);
      setCard(c);
      setStatus("ready");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Backtest failed");
      setStatus("error");
    }
  }

  return (
    <section className="card backtest">
      <div className="dashboard-head">
        <h2>Backtest scorecard</h2>
        <span className="dashboard-sub">
          Historical replay · forecast-vs-actual, exact-arithmetic scores (SPEC §25)
        </span>
      </div>

      <div className="bt-case">
        {benchmark ? (
          <>
            <div className="bt-case-head">
              <span className="bt-case-name">{benchmark.name}</span>
              <span className={`tag ${benchmark.actuals_provenance.toLowerCase()}`}>
                actuals: {benchmark.actuals_provenance}
              </span>
            </div>
            {benchmark.description && (
              <p className="bt-case-desc">{benchmark.description}</p>
            )}
            <p className="hint bt-case-note">{benchmark.actuals_note}</p>
          </>
        ) : (
          <p className="hint">
            Replays the engine&rsquo;s built-in benchmark case. Waiting for the
            backend to serve it…
          </p>
        )}
      </div>

      <div className="policy-actions" style={{ marginTop: 0 }}>
        <button
          type="button"
          className="btn primary"
          onClick={score}
          disabled={status === "loading"}
        >
          {status === "loading"
            ? "Scoring…"
            : card
              ? "Re-run backtest"
              : "Run backtest"}
        </button>
        {card && <span className="tag simulated">Forecast Simulated</span>}
      </div>

      {status === "error" && (
        <p className="hint error-text">Couldn&rsquo;t run backtest: {error}</p>
      )}

      {card && status === "ready" && (
        <div className="bt-body">
          <div className="bt-metrics">
            <ScoreStat label="MAE" value={formatNumber(card.mae)} hint="mean abs error" />
            <ScoreStat label="RMSE" value={formatNumber(card.rmse)} hint="root-mean-sq error" />
            <ScoreStat
              label="MAPE"
              value={card.mape_pct != null ? `${card.mape_pct.toFixed(1)}%` : "—"}
              hint="mean abs % error"
            />
            <ScoreStat
              label="Direction"
              value={`${Math.round(card.direction_accuracy_pct)}%`}
              hint="right sign vs baseline"
              good={card.direction_accuracy_pct >= 60}
            />
            <ScoreStat
              label="Coverage"
              value={`${Math.round(card.interval_coverage_pct)}%`}
              hint="actuals in band (calibration)"
              good={card.interval_coverage_pct >= 60}
            />
            {card.mean_event_timing_error_months != null && (
              <ScoreStat
                label="Event timing"
                value={`${card.mean_event_timing_error_months.toFixed(1)} mo`}
                hint="mean |pred − actual|"
              />
            )}
          </div>

          <div className="bt-actuals-banner">
            <span className={`tag ${card.actuals_provenance.toLowerCase()}`}>
              actuals: {card.actuals_provenance}
            </span>
            <span>{card.actuals_note}</span>
          </div>

          {card.summary && <p className="bt-summary">{card.summary}</p>}

          <h3 className="bt-sub">
            Per-metric forecast vs actual · {card.n_observations} observations
          </h3>
          <div className="bt-table" role="table" aria-label="Forecast vs actual by metric">
            <div className="bt-row bt-row-head" role="row">
              <span role="columnheader">Metric</span>
              <span role="columnheader">@mo</span>
              <span role="columnheader">Forecast</span>
              <span role="columnheader">Actual</span>
              <span role="columnheader">Error</span>
              <span role="columnheader">Dir</span>
              <span role="columnheader">Band</span>
            </div>
            {card.metric_scores.map((s, i) => (
              <MetricRow key={`${s.metric_key}-${s.t_months}-${i}`} s={s} />
            ))}
          </div>

          <p className="hint bt-note">{card.note}</p>
        </div>
      )}
    </section>
  );
}

function ScoreStat({
  label,
  value,
  hint,
  good,
}: {
  label: string;
  value: string;
  hint: string;
  good?: boolean;
}) {
  return (
    <div className={`bt-stat${good === true ? " good" : good === false ? " warn" : ""}`}>
      <span className="bt-stat-label">{label}</span>
      <span className="bt-stat-val">{value}</span>
      <span className="bt-stat-hint">{hint}</span>
    </div>
  );
}

function MetricRow({ s }: { s: MetricScore }) {
  const shortKey = s.metric_key.split(".").pop() ?? s.metric_key;
  return (
    <div className="bt-row" role="row">
      <span role="cell" className="bt-metric-key" title={s.metric_key}>
        {shortKey}
      </span>
      <span role="cell">{s.t_months}</span>
      <span role="cell">{formatNumber(s.forecast)}</span>
      <span role="cell">{formatNumber(s.actual)}</span>
      <span
        role="cell"
        className={`bt-err ${s.abs_error === 0 ? "flat" : "num"}`}
        title={s.pct_error != null ? `${s.pct_error.toFixed(1)}%` : undefined}
      >
        {s.error > 0 ? "+" : ""}
        {formatNumber(s.error)}
      </span>
      <span role="cell" className={s.direction_correct ? "bt-ok" : "bt-no"}>
        {s.direction_correct ? "✓" : "✗"}
      </span>
      <span role="cell" className={s.within_interval ? "bt-ok" : "bt-no"}>
        {s.within_interval ? "✓" : "✗"}
      </span>
    </div>
  );
}
