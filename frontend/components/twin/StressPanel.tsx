"use client";

/**
 * Stress-testing environment (SPEC §20): does the policy's benefit survive
 * external shocks? Built by `POST /stress-test`, which re-runs the deterministic
 * A/B/Δ core once per named shock (recession, fuel-price spike, flood, heatwave,
 * population growth, migration change, technology adoption, interest-rate shock)
 * plus a no-shock reference. Each shock is a transparent scenario assumption
 * applied to BOTH worlds, so Δ(B−A) keeps isolating the policy — and comparing
 * the shocked delta to the no-shock delta answers SPEC §20 directly: *this policy
 * holds under X but fails under Z.*
 *
 * Honesty story (SPEC §20/§34): policy deltas are Simulated by a deterministic
 * model (no LLM); shock magnitudes are Estimated scenario inputs, shown with each
 * scenario's `fidelity` (modelled/partial/proxy), horizon-aware `confidence` and a
 * plain-language `caveat`, plus the exact auditable `overrides`. The shock toggles
 * come from `GET /stress-test/catalogue`. When the backend is down we show a clear
 * waiting/error state; we never invent a robustness claim.
 */

import { useEffect, useState } from "react";

import { fetchStressCatalogue, runStressTest } from "../../lib/api";
import type {
  MetricStress,
  ScenarioResult,
  ShockCard,
  StressReport,
} from "../../lib/api";
import { useTwin } from "./TwinStore";

type Status = "idle" | "loading" | "ready" | "error";

/** Horizon options; confidence widens with the horizon (SPEC §24). */
const HORIZONS: Array<{ months: number; label: string }> = [
  { months: 12, label: "1 year" },
  { months: 24, label: "2 years" },
  { months: 60, label: "5 years" },
  { months: 120, label: "10 years" },
];

/** Scenario verdict → tone. */
function scenarioTone(verdict: string): "good" | "mid" | "bad" | "muted" {
  if (verdict === "fails") return "bad";
  if (verdict === "degrades") return "mid";
  if (verdict === "holds") return "good";
  return "muted"; // reference
}

/** Metric verdict → tone. */
function metricTone(verdict: string): "good" | "mid" | "bad" | "muted" {
  if (verdict === "reversed" || verdict === "neutralised") return "bad";
  if (verdict === "weakened") return "mid";
  if (verdict === "robust" || verdict === "strengthened") return "good";
  return "muted"; // n/a
}

function confidenceTone(confidence: string): "good" | "mid" | "bad" {
  if (confidence === "high") return "good";
  if (confidence === "medium") return "mid";
  return "bad";
}

function signed(v: number, digits = 2): string {
  const sign = v > 0 ? "+" : v < 0 ? "−" : "";
  return `${sign}${Math.abs(v).toFixed(digits)}`;
}

function signedPct(v: number | null): string {
  if (v == null) return "";
  const sign = v > 0 ? "+" : v < 0 ? "−" : "";
  return `${sign}${Math.abs(v).toFixed(1)}%`;
}

export default function StressPanel() {
  const { policy } = useTwin();
  const [status, setStatus] = useState<Status>("idle");
  const [report, setReport] = useState<StressReport | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [catalogue, setCatalogue] = useState<ShockCard[] | null>(null);
  const [catError, setCatError] = useState<string | null>(null);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [horizon, setHorizon] = useState<number>(60);

  // Reset when the policy changes (a new policy invalidates any prior run).
  useEffect(() => {
    setReport(null);
    setStatus("idle");
    setError(null);
  }, [policy]);

  // Load the shock catalogue once a policy exists so the user can toggle shocks.
  useEffect(() => {
    if (!policy) return;
    let live = true;
    const ctrl = new AbortController();
    (async () => {
      try {
        const cat = await fetchStressCatalogue(ctrl.signal);
        if (!live) return;
        setCatalogue(cat.scenarios);
        setSelected(new Set(cat.scenarios.map((s) => s.key)));
        setCatError(null);
      } catch (e: unknown) {
        if (!live) return;
        // Catalogue unavailable → fall back to "all shocks" (undefined selection).
        setCatalogue(null);
        setCatError(e instanceof Error ? e.message : "catalogue unavailable");
      }
    })();
    return () => {
      live = false;
      ctrl.abort();
    };
  }, [policy]);

  function toggle(key: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }

  async function run() {
    if (!policy) return;
    setStatus("loading");
    setError(null);
    try {
      // If we have a catalogue, honour the toggles (all → send undefined so the
      // backend applies its full default set). Otherwise run all shocks.
      const keys =
        catalogue && selected.size > 0 && selected.size < catalogue.length
          ? Array.from(selected)
          : null;
      const r = await runStressTest(policy, keys, horizon);
      setReport(r);
      setStatus("ready");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Stress test failed");
      setStatus("error");
    }
  }

  const allSelected = catalogue ? selected.size === catalogue.length : true;
  const noneSelected = catalogue ? selected.size === 0 : false;

  return (
    <section className="card stress">
      <div className="dashboard-head">
        <h2>Stress-testing environment</h2>
        <span className="dashboard-sub">
          Does the policy&rsquo;s benefit survive external shocks? (SPEC §20)
        </span>
      </div>

      {!policy ? (
        <div className="waiting">
          <span className="tag muted">No policy yet</span>
          <p>
            Compile a policy above to re-run it across named external shocks —
            recession, fuel-price spike, flood, heatwave, population growth,
            migration change, technology adoption, interest-rate shock — and see
            where its benefit holds, degrades or fails.
          </p>
        </div>
      ) : (
        <>
          {catalogue && catalogue.length > 0 && (
            <div className="st-shocks" data-tour="stress-shocks">
              <div className="st-shocks-head">
                <span className="st-shocks-title">Shocks to test</span>
                <div className="st-shocks-actions">
                  <button
                    type="button"
                    className="st-mini"
                    onClick={() =>
                      setSelected(new Set(catalogue.map((s) => s.key)))
                    }
                    disabled={allSelected}
                  >
                    All
                  </button>
                  <button
                    type="button"
                    className="st-mini"
                    onClick={() => setSelected(new Set())}
                    disabled={noneSelected}
                  >
                    None
                  </button>
                </div>
              </div>
              <div className="st-chips">
                {catalogue.map((s) => {
                  const on = selected.has(s.key);
                  return (
                    <button
                      key={s.key}
                      type="button"
                      className={`st-chip${on ? " on" : ""}`}
                      aria-pressed={on}
                      onClick={() => toggle(s.key)}
                      title={`${s.description}\n${s.rationale}`}
                    >
                      <span className="st-chip-label">{s.label}</span>
                      <span className={`st-fid ${s.fidelity}`}>{s.fidelity}</span>
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {catError && !catalogue && (
            <p className="hint">
              Shock catalogue unavailable ({catError}) — the run will test the full
              default set of SPEC §20 shocks.
            </p>
          )}

          <div className="policy-actions st-controls" style={{ marginTop: 0 }}>
            <label className="st-horizon">
              <span>Horizon</span>
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
              disabled={status === "loading" || noneSelected}
            >
              {status === "loading"
                ? "Stress-testing…"
                : report
                  ? "Re-run stress test"
                  : "Run stress test"}
            </button>
            {noneSelected && (
              <span className="hint" style={{ margin: 0 }}>
                Select at least one shock.
              </span>
            )}
            {report && (
              <span className={`tag ${report.provenance.toLowerCase()}`}>
                {report.provenance}
              </span>
            )}
          </div>

          {status === "error" && (
            <p className="hint error-text">
              Couldn&rsquo;t run stress test: {error}
            </p>
          )}

          {status === "idle" && !report && (
            <p className="hint">
              Each shock is a transparent scenario assumption applied to BOTH
              worlds, so Δ(B−A) still isolates the policy. Policy deltas are
              Simulated (deterministic, no LLM); shock magnitudes are Estimated.
              Click to run.
            </p>
          )}

          {report && status !== "loading" && (
            <div className="st-body">
              <RobustnessBanner r={report} />

              <ScenarioCard result={report.baseline} isBaseline />

              {report.scenarios.map((s) => (
                <ScenarioCard key={s.key} result={s} />
              ))}

              <p className="hint eco-note">{report.note}</p>
            </div>
          )}
        </>
      )}
    </section>
  );
}

function RobustnessBanner({ r }: { r: StressReport }) {
  const rb = r.robustness;
  const cols: Array<{
    key: string;
    title: string;
    keys: string[];
    tone: "good" | "mid" | "bad";
  }> = [
    { key: "holds", title: "Holds", keys: rb.robust_to, tone: "good" },
    { key: "degrades", title: "Degrades", keys: rb.degrades_under, tone: "mid" },
    { key: "fails", title: "Fails", keys: rb.fails_under, tone: "bad" },
  ];
  return (
    <div className="st-robust">
      <p className="st-robust-headline">{rb.headline}</p>
      <span className="st-robust-sub">
        Robustness at {r.horizon_label} horizon
      </span>
      <div className="st-robust-cols">
        {cols.map((c) => (
          <div key={c.key} className={`st-robust-col ${c.tone}`}>
            <div className="st-robust-count">{c.keys.length}</div>
            <div className="st-robust-title">{c.title}</div>
            <div className="st-robust-keys">
              {c.keys.length === 0 ? (
                <span className="st-robust-none">—</span>
              ) : (
                c.keys.map((k) => (
                  <span key={k} className="st-robust-key">
                    {k.replace(/_/g, " ")}
                  </span>
                ))
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function ScenarioCard({
  result,
  isBaseline = false,
}: {
  result: ScenarioResult;
  isBaseline?: boolean;
}) {
  const tone = scenarioTone(result.verdict);
  const overrides = Object.entries(result.overrides ?? {});
  return (
    <div className={`st-scenario ${tone}${isBaseline ? " st-baseline" : ""}`}>
      <div className="st-scen-head">
        <div className="st-scen-heading">
          <span className="st-scen-label">{result.label}</span>
          <span className="st-scen-cat">{result.category}</span>
        </div>
        <div className="st-scen-badges">
          {!isBaseline && (
            <span className={`st-fid ${result.fidelity}`}>{result.fidelity}</span>
          )}
          <span className={`st-conf ${confidenceTone(result.confidence)}`}>
            {result.confidence} confidence
          </span>
          <span className={`st-verdict ${tone}`}>
            {isBaseline ? "reference" : result.verdict}
          </span>
        </div>
      </div>

      <p className="st-scen-summary">{result.summary}</p>

      {result.metrics.length > 0 && (
        <div className="st-metric-table" role="table" aria-label={result.label}>
          <div className="st-metric-row st-metric-head" role="row">
            <span role="columnheader">Metric</span>
            <span role="columnheader" title="Policy Δ(B−A) with no shock">
              Δ no-shock
            </span>
            <span role="columnheader" title="Policy Δ(B−A) under this shock">
              Δ shocked
            </span>
            <span role="columnheader" title="Benefit retained vs no-shock">
              retained
            </span>
          </div>
          {result.metrics.map((m) => (
            <MetricRow key={m.key} m={m} isBaseline={isBaseline} />
          ))}
        </div>
      )}

      {!isBaseline && result.caveat && (
        <p className="st-caveat">
          <span className="st-caveat-tag">fidelity caveat</span>
          {result.caveat}
        </p>
      )}

      {isBaseline && result.caveat && (
        <p className="hint st-baseline-caveat">{result.caveat}</p>
      )}

      {!isBaseline && overrides.length > 0 && (
        <details className="st-overrides">
          <summary>
            Scenario overrides{" "}
            <span className="eco-assum-count">({overrides.length})</span>
            <span className="tag estimated st-ov-tag">Estimated</span>
          </summary>
          <dl>
            {overrides.map(([k, v]) => (
              <div key={k} className="eco-assum-row">
                <dt>{k.replace(/_/g, " ")}</dt>
                <dd>{v == null ? "—" : String(v)}</dd>
              </div>
            ))}
          </dl>
        </details>
      )}
    </div>
  );
}

function MetricRow({
  m,
  isBaseline,
}: {
  m: MetricStress;
  isBaseline: boolean;
}) {
  const tone = metricTone(m.verdict);
  // Retained-benefit bar: 100% = unchanged; clamp the fill to [0, 150].
  const retained = m.retained_pct;
  const fill =
    retained == null ? 0 : Math.max(0, Math.min(150, retained)) / 150;
  return (
    <div className="st-metric-row" role="row" title={m.note}>
      <span className="st-metric-name" role="cell">
        {m.label}
        <span className="st-metric-unit">{m.unit}</span>
      </span>
      <span className="st-metric-delta" role="cell">
        {signed(m.delta_baseline)}
        {m.delta_baseline_pct != null && (
          <span className="st-metric-pct"> {signedPct(m.delta_baseline_pct)}</span>
        )}
      </span>
      <span className="st-metric-delta" role="cell">
        {signed(m.delta_shocked)}
        {m.delta_shocked_pct != null && (
          <span className="st-metric-pct"> {signedPct(m.delta_shocked_pct)}</span>
        )}
      </span>
      <span className="st-metric-retained" role="cell">
        {isBaseline ? (
          <span className="st-metric-ref">reference</span>
        ) : (
          <>
            <span className="st-retain-track">
              <span
                className={`st-retain-fill ${tone}`}
                style={{ width: `${fill * 100}%` }}
              />
              <span className="st-retain-100" title="100% = benefit unchanged" />
            </span>
            <span className={`st-retain-val ${tone}`}>
              {retained == null ? "n/a" : `${retained.toFixed(0)}%`}
            </span>
            <span className={`st-verdict sm ${tone}`}>{m.verdict}</span>
          </>
        )}
      </span>
    </div>
  );
}
