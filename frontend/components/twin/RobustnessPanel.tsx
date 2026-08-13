"use client";

/**
 * Decision under uncertainty (SPEC §20/§21/§22): one level up from the Stress
 * tab. The stress test asks *"does **this** policy hold under the named shocks?"*.
 * This tab asks the decision question a minister actually faces: *"given several
 * candidate policies and a set of possible futures, **which candidate should I
 * pick** — the headline winner, or the one that is least bad when the world turns
 * out otherwise?"*.
 *
 * Built by `POST /robustness`, which scores each candidate under the transparent
 * baseline plus the SPEC §20 named shocks, builds the regret matrix, and reports
 * which candidate each classic decision criterion selects: the nominal winner,
 * the maximin (worst-case) choice, the minimax-regret (Savage) choice, the
 * Laplace (equal-weight) choice, and the stress-test robustness rate.
 *
 * Candidate sourcing (honesty, SPEC §34): the compiled policy is candidate one;
 * the alternatives are **transparent design variants of that same policy**,
 * derived client-side through the exact structured amendment loop the app already
 * uses (`applyAmendment`) — halve/raise the charge, redirect revenue, exempt
 * low-income. No number is invented here: each variant is a compiled DSL the
 * backend re-simulates through the same deterministic A/B/Δ core, so a candidate's
 * payoffs can never disagree with the Stress/Simulate tabs. Every payoff is a
 * Simulated Δ(B−A); no randomness, no LLM touches the numeric path. When the
 * backend is down we show a clear waiting/error state and never mint a decision.
 */

import { useEffect, useMemo, useState } from "react";

import {
  applyAmendment,
  fetchRobustnessObjectives,
  runRobustness,
} from "../../lib/api";
import type {
  Amendment,
  PolicyDSL,
  RobustnessCandidateScore,
  RobustnessReport,
} from "../../lib/api";
import { formatNumber } from "../../lib/format";
import { useTwin } from "./TwinStore";

type Status = "idle" | "loading" | "ready" | "error";

/** Horizon options; confidence widens with the horizon (SPEC §24). */
const HORIZONS: Array<{ months: number; label: string }> = [
  { months: 12, label: "1 year" },
  { months: 24, label: "2 years" },
  { months: 60, label: "5 years" },
  { months: 120, label: "10 years" },
];

/**
 * Transparent alternative designs, each an `applyAmendment` on the compiled
 * policy (the same structured edit the amendment loop uses). The compiled policy
 * itself is always the first, un-amended candidate.
 */
const VARIANTS: Array<{ key: string; label: string; amend: Amendment }> = [
  { key: "half", label: "Half charge", amend: { label: "Half charge", charge_multiplier: 0.5 } },
  { key: "higher", label: "Higher charge", amend: { label: "Higher charge", charge_multiplier: 1.5 } },
  {
    key: "transit",
    label: "Transit-funded",
    amend: { label: "Transit-funded", set_public_transport_share: 1.0 },
  },
  {
    key: "genfund",
    label: "General-fund",
    amend: { label: "General-fund", set_public_transport_share: 0.0 },
  },
  {
    key: "exempt",
    label: "Low-income exempt",
    amend: { label: "Low-income exempt", exempt_low_income: true },
  },
];

/** Default variant slate (kept small + non-redundant for a legible demo). */
const DEFAULT_VARIANTS = new Set(["half", "transit"]);

/** Friendly labels for the four headline objectives; falls back to the raw key. */
const OBJECTIVE_LABELS: Record<string, string> = {
  "traffic.vehicle_trips_into_cbd": "Vehicle trips into CBD",
  "emissions.daily_co2_tonnes": "Daily CO₂ (tonnes)",
  "mode_share.car_pct": "Car mode share",
  "transit.daily_transit_trips": "Daily transit trips",
};

function objectiveLabel(key: string): string {
  return OBJECTIVE_LABELS[key] ?? key.replace(/[._]/g, " ");
}

function signed(v: number): string {
  const sign = v > 0 ? "+" : v < 0 ? "−" : "";
  return `${sign}${formatNumber(Math.abs(v))}`;
}

function confidenceTone(c: string): "good" | "mid" | "bad" {
  if (c === "high") return "good";
  if (c === "medium") return "mid";
  return "bad";
}

export default function RobustnessPanel() {
  const { policy } = useTwin();
  const [status, setStatus] = useState<Status>("idle");
  const [report, setReport] = useState<RobustnessReport | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [objectives, setObjectives] = useState<string[] | null>(null);
  const [objective, setObjective] = useState<string>("");
  const [horizon, setHorizon] = useState<number>(60);
  const [variants, setVariants] = useState<Set<string>>(new Set(DEFAULT_VARIANTS));

  // Reset when the policy changes (a new policy invalidates any prior decision).
  useEffect(() => {
    setReport(null);
    setStatus("idle");
    setError(null);
  }, [policy]);

  // Load the objective menu once a policy exists.
  useEffect(() => {
    if (!policy) return;
    let live = true;
    const ctrl = new AbortController();
    (async () => {
      try {
        const o = await fetchRobustnessObjectives(ctrl.signal);
        if (!live) return;
        setObjectives(o.objectives);
        setObjective((prev) => prev || o.default);
      } catch {
        if (!live) return;
        // Objective menu unavailable → run with the backend default (undefined).
        setObjectives(null);
      }
    })();
    return () => {
      live = false;
      ctrl.abort();
    };
  }, [policy]);

  // The candidate set: the compiled policy + each selected design variant.
  const candidates = useMemo<PolicyDSL[]>(() => {
    if (!policy) return [];
    const base = policy as PolicyDSL;
    const derived = VARIANTS.filter((v) => variants.has(v.key)).map((v) =>
      applyAmendment(base, v.amend),
    );
    return [base, ...derived];
  }, [policy, variants]);

  function toggleVariant(key: string) {
    setVariants((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }

  async function run() {
    if (!policy || candidates.length < 2) return;
    setStatus("loading");
    setError(null);
    try {
      const r = await runRobustness(candidates, {
        objective: objective || null,
        horizonMonths: horizon,
      });
      setReport(r);
      setStatus("ready");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Robustness comparison failed");
      setStatus("error");
    }
  }

  return (
    <section className="card robustness">
      <div className="dashboard-head">
        <h2>Decision under uncertainty</h2>
        <span className="dashboard-sub">
          Which candidate should a minister pick once the future is uncertain?
          (SPEC §20/§21/§22)
        </span>
      </div>

      {!policy ? (
        <div className="waiting">
          <span className="tag muted">No policy yet</span>
          <p>
            Compile a policy above. This tab compares it against transparent
            design variants across the baseline and every SPEC §20 shock, then
            reports which candidate each decision rule picks — the headline
            winner, the worst-case (maximin) choice, the least-regret (Savage)
            choice and the most robust. Often the headline winner is <em>not</em>{" "}
            the one you should choose.
          </p>
        </div>
      ) : (
        <>
          <div className="rb-candidates">
            <div className="rb-candidates-head">
              <span className="rb-candidates-title">
                Candidates ({candidates.length})
              </span>
              <span className="rb-candidates-note">
                Your compiled policy + transparent design variants (same amendment
                loop, backend-simulated)
              </span>
            </div>
            <div className="rb-chips">
              <span className="rb-chip base" title="Your compiled policy (un-amended)">
                Your policy
              </span>
              {VARIANTS.map((v) => {
                const on = variants.has(v.key);
                return (
                  <button
                    key={v.key}
                    type="button"
                    className={`rb-chip${on ? " on" : ""}`}
                    aria-pressed={on}
                    onClick={() => toggleVariant(v.key)}
                  >
                    {v.label}
                  </button>
                );
              })}
            </div>
          </div>

          <div className="policy-actions rb-controls" style={{ marginTop: 0 }}>
            <label className="rb-field">
              <span>Objective</span>
              <select
                value={objective}
                onChange={(e) => setObjective(e.target.value)}
                disabled={!objectives}
              >
                {objectives ? (
                  objectives.map((k) => (
                    <option key={k} value={k}>
                      {objectiveLabel(k)}
                    </option>
                  ))
                ) : (
                  <option value="">backend default</option>
                )}
              </select>
            </label>
            <label className="rb-field">
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
              disabled={status === "loading" || candidates.length < 2}
            >
              {status === "loading"
                ? "Comparing…"
                : report
                  ? "Re-run comparison"
                  : "Compare under uncertainty"}
            </button>
            {candidates.length < 2 && (
              <span className="hint" style={{ margin: 0 }}>
                Select at least one variant (need ≥2 candidates).
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
              Couldn&rsquo;t compare candidates: {error}
            </p>
          )}

          {status === "idle" && !report && (
            <p className="hint">
              Each candidate is scored under the baseline plus the SPEC §20 shocks;
              payoffs are the same Simulated Δ(B−A) the Stress tab returns
              (deterministic, no LLM). Regret is per-state best-payoff minus the
              candidate&rsquo;s. Click to run the decision analysis.
            </p>
          )}

          {report && status !== "loading" && <RobustnessResult report={report} />}
        </>
      )}
    </section>
  );
}

function RobustnessResult({ report }: { report: RobustnessReport }) {
  const byId = useMemo(() => {
    const m = new Map<string, RobustnessCandidateScore>();
    for (const c of report.candidates) m.set(c.policy_id, c);
    return m;
  }, [report]);

  const labelFor = (id: string | null): string => {
    if (!id) return "—";
    return byId.get(id)?.label ?? id;
  };

  const nominal = report.picks.nominal_best;
  // The demo's point: does admitting uncertainty change the choice?
  const robustDiffers =
    report.picks.maximin !== nominal ||
    report.picks.minimax_regret !== nominal ||
    report.picks.most_robust !== nominal;

  const criteria: Array<{
    key: string;
    title: string;
    hint: string;
    pick: string | null;
  }> = [
    { key: "nominal", title: "Headline (nominal)", hint: "Best baseline payoff", pick: report.picks.nominal_best },
    { key: "maximin", title: "Worst-case (maximin)", hint: "Best if the worst state hits", pick: report.picks.maximin },
    {
      key: "savage",
      title: "Least-regret (Savage)",
      hint: "Lowest max regret",
      pick: report.picks.minimax_regret,
    },
    { key: "laplace", title: "Equal-weight (Laplace)", hint: "Best mean payoff", pick: report.picks.laplace },
    { key: "robust", title: "Most robust", hint: "Holds under most shocks", pick: report.picks.most_robust },
  ];

  return (
    <div className="rb-body">
      <div className={`rb-headline ${robustDiffers ? "flips" : "agrees"}`}>
        <span className="rb-headline-badge">
          {robustDiffers ? "Robustness flips the choice" : "Choice is robust"}
        </span>
        <p className="rb-headline-text">{report.headline}</p>
        <span className="rb-headline-sub">
          Objective: <strong>{report.objective_label}</strong> (
          {report.objective_direction}) · {report.horizon_label} horizon ·{" "}
          {report.states.length} states
        </span>
      </div>

      <div className="rb-picks">
        {criteria.map((c) => {
          const same = c.pick === nominal;
          return (
            <div
              key={c.key}
              className={`rb-pick${c.key === "nominal" ? " nominal" : same ? " agree" : " differ"}`}
            >
              <div className="rb-pick-title">{c.title}</div>
              <div className="rb-pick-name">{labelFor(c.pick)}</div>
              <div className="rb-pick-hint">{c.hint}</div>
            </div>
          );
        })}
      </div>

      <div className="rb-scores">
        <h3>Candidate scorecard</h3>
        <div className="rb-table-wrap">
          <table className="rb-table">
            <thead>
              <tr>
                <th className="rb-left">Candidate</th>
                <th>Nominal</th>
                <th>Worst-case</th>
                <th>Mean</th>
                <th>Max regret</th>
                <th>Robustness</th>
              </tr>
            </thead>
            <tbody>
              {report.candidates.map((c) => (
                <tr key={c.policy_id} className={c.policy_id === nominal ? "rb-row-nominal" : ""}>
                  <td className="rb-left">
                    <span className="rb-cand-label">{c.label}</span>
                    <span className="rb-cand-id">{c.policy_id}</span>
                  </td>
                  <td>{signed(c.nominal_payoff)}</td>
                  <td>{signed(c.worst_case_payoff)}</td>
                  <td>{signed(c.mean_payoff)}</td>
                  <td>{formatNumber(c.max_regret)}</td>
                  <td>
                    <span className="rb-robust-cell">
                      {Math.round(c.robustness_score * 100)}%
                      <span className="rb-robust-detail">
                        holds {c.holds_under.length} · fails {c.fails_under.length}
                      </span>
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="hint rb-scores-note">
          Payoff is signed so higher = a better effect on{" "}
          {report.objective_label}. Max regret is the largest &ldquo;I wish
          I&rsquo;d chosen otherwise&rdquo; gap across states (lower is better).
          Robustness is the share of shocks where a candidate keeps ≥75% of its
          own no-shock benefit.
        </p>
      </div>

      <RegretMatrix report={report} nominal={nominal} />

      <details className="rb-method">
        <summary>Method &amp; provenance</summary>
        <p>{report.method}</p>
      </details>
    </div>
  );
}

function RegretMatrix({
  report,
  nominal,
}: {
  report: RobustnessReport;
  nominal: string | null;
}) {
  // State labels come from the first candidate's per-state rows (all candidates
  // share the same ordered state set).
  const stateMeta = report.candidates[0]?.states ?? [];
  return (
    <div className="rb-matrix">
      <h3>Regret matrix</h3>
      <span className="rb-matrix-sub">
        Per state: how much worse each candidate is than the best candidate for
        that state (0 = best here). The maximum in each row is its max regret.
      </span>
      <div className="rb-table-wrap">
        <table className="rb-table rb-matrix-table">
          <thead>
            <tr>
              <th className="rb-left">Candidate</th>
              {stateMeta.map((s) => (
                <th key={s.state_key} title={`${s.category} · confidence ${s.confidence}`}>
                  <span className="rb-state-label">{s.state_label}</span>
                  <span className={`rb-state-conf ${confidenceTone(s.confidence)}`}>
                    {s.confidence}
                  </span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {report.candidates.map((c) => (
              <tr key={c.policy_id} className={c.policy_id === nominal ? "rb-row-nominal" : ""}>
                <td className="rb-left">{c.label}</td>
                {c.states.map((st) => {
                  const best = st.regret <= 1e-9;
                  const worst = Math.abs(st.regret - c.max_regret) <= 1e-9 && !best;
                  return (
                    <td
                      key={st.state_key}
                      className={`rb-cell${best ? " best" : ""}${worst ? " worst" : ""}`}
                      title={`payoff ${signed(st.payoff)} · regret ${formatNumber(st.regret)}`}
                    >
                      {best ? "0" : formatNumber(st.regret)}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
