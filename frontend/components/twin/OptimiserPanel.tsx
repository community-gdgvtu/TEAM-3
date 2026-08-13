"use client";

/**
 * Policy optimiser view (SPEC §22): works the problem backwards. Given an
 * objective + constraints, `POST /optimise` grid-searches candidate interventions,
 * simulates each with the deterministic model, keeps the feasible ones, builds a
 * Pareto frontier, and labels representative picks (cheapest / most equitable /
 * largest emissions cut / best balanced).
 *
 * This tab is policy-independent — it searches the candidate space, it doesn't need
 * a compiled policy. Honesty (SPEC §22/§34): outcome metrics are Simulated from the
 * same model as every other endpoint; the only non-simulated number is a
 * transparent, documented cost proxy (Estimated) used for the budget constraint —
 * flagged as such and never LLM-produced. When the backend is down we say so.
 */

import { useState } from "react";

import { runOptimise } from "../../lib/api";
import type { OptimiserCandidate, OptimiserResult } from "../../lib/api";
import { formatNumber } from "../../lib/format";

type Status = "idle" | "loading" | "ready" | "error";

function pct(v: number): string {
  return `${v > 0 ? "+" : ""}${v.toFixed(1)}%`;
}

/** Money proxy, compact (e.g. 120000000 → "$120M"). Estimated, not simulated. */
function money(v: number): string {
  if (Math.abs(v) >= 1e9) return `$${(v / 1e9).toFixed(1)}B`;
  if (Math.abs(v) >= 1e6) return `$${(v / 1e6).toFixed(0)}M`;
  if (Math.abs(v) >= 1e3) return `$${(v / 1e3).toFixed(0)}k`;
  return `$${formatNumber(v)}`;
}

export default function OptimiserPanel() {
  const [status, setStatus] = useState<Status>("idle");
  const [result, setResult] = useState<OptimiserResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Optional constraint knobs (blank = unconstrained on that axis).
  const [maxCommute, setMaxCommute] = useState("");
  const [maxBurden, setMaxBurden] = useState("");
  const [maxBudgetM, setMaxBudgetM] = useState("");

  async function optimise() {
    setStatus("loading");
    setError(null);
    const constraints: Record<string, unknown> = {};
    if (maxCommute.trim() !== "")
      constraints.max_average_commute_increase_pct = Number(maxCommute);
    if (maxBurden.trim() !== "")
      constraints.max_low_income_burden_increase_pct = Number(maxBurden);
    if (maxBudgetM.trim() !== "") constraints.max_budget = Number(maxBudgetM) * 1e6;
    try {
      const r = await runOptimise({}, constraints);
      setResult(r);
      setStatus("ready");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Optimiser failed");
      setStatus("error");
    }
  }

  const byId = new Map((result?.candidates ?? []).map((c) => [c.policy_id, c]));
  const recs = result?.recommendations;
  const recCards: Array<{ label: string; id: string | null }> = recs
    ? [
        { label: "Cheapest", id: recs.cheapest },
        { label: "Most equitable", id: recs.most_equitable },
        { label: "Largest CO₂ cut", id: recs.largest_emissions_reduction },
        { label: "Best balanced", id: recs.best_balanced },
      ]
    : [];

  return (
    <section className="card optimiser">
      <div className="dashboard-head">
        <h2>Policy optimiser</h2>
        <span className="dashboard-sub">
          Objective + constraints → feasible Pareto frontier (SPEC §22)
        </span>
      </div>

      <div className="opt-constraints">
        <span className="opt-con-label">Constraints (optional):</span>
        <label className="opt-con">
          max commute +%
          <input
            type="number"
            value={maxCommute}
            onChange={(e) => setMaxCommute(e.target.value)}
            placeholder="—"
          />
        </label>
        <label className="opt-con">
          max low-income +%
          <input
            type="number"
            value={maxBurden}
            onChange={(e) => setMaxBurden(e.target.value)}
            placeholder="—"
          />
        </label>
        <label className="opt-con">
          max budget ($M)
          <input
            type="number"
            value={maxBudgetM}
            onChange={(e) => setMaxBudgetM(e.target.value)}
            placeholder="—"
          />
        </label>
      </div>

      <div className="policy-actions" style={{ marginTop: "0.5rem" }}>
        <button
          type="button"
          className="btn primary"
          onClick={optimise}
          disabled={status === "loading"}
        >
          {status === "loading" ? "Searching…" : result ? "Re-optimise" : "Optimise"}
        </button>
        {result && <span className="tag simulated">Outcomes Simulated · cost Estimated</span>}
      </div>

      {status === "error" && (
        <p className="hint error-text">Couldn&rsquo;t optimise: {error}</p>
      )}

      {status === "idle" && !result && (
        <p className="hint">
          Grid-searches candidate interventions, simulates each, and returns the
          feasible trade-off frontier. Runs without a compiled policy.
        </p>
      )}

      {result && status !== "loading" && (
        <div className="opt-body">
          <div className={`opt-feas ${result.constraints_satisfiable ? "ok" : "bad"}`}>
            <span className="opt-feas-mark">
              {result.constraints_satisfiable ? "✓" : "✗"}
            </span>
            <span>
              {result.n_feasible}/{result.n_candidates} candidates feasible ·{" "}
              {result.pareto_front.length} on the Pareto frontier
              {!result.constraints_satisfiable && " · no candidate meets every constraint"}
            </span>
          </div>

          {recCards.some((c) => c.id) && (
            <div className="opt-recs">
              {recCards.map((c) => {
                const cand = c.id ? byId.get(c.id) : undefined;
                return (
                  <div className="opt-rec" key={c.label}>
                    <span className="opt-rec-role">{c.label}</span>
                    {cand ? (
                      <>
                        <span className="opt-rec-name">{cand.label}</span>
                        <span className="opt-rec-metrics">
                          CO₂ {pct(cand.metrics.emissions_reduction_pct)} · burden{" "}
                          {pct(cand.metrics.low_income_burden_pct)} · {money(cand.metrics.est_cost)}
                        </span>
                      </>
                    ) : (
                      <span className="opt-rec-name muted">—</span>
                    )}
                  </div>
                );
              })}
            </div>
          )}

          <h3 className="opt-sub">Pareto frontier · {result.pareto_front.length}</h3>
          <p className="opt-axes">
            trades off: {result.objective_axes.join(" · ") || "emissions / equity / support / cost"}
          </p>
          <div className="opt-table" role="table" aria-label="Pareto frontier candidates">
            <div className="opt-row opt-row-head" role="row">
              <span role="columnheader">Candidate</span>
              <span role="columnheader" className="opt-num">CO₂ ↓</span>
              <span role="columnheader" className="opt-num">Traffic ↓</span>
              <span role="columnheader" className="opt-num">Commute ↑</span>
              <span role="columnheader" className="opt-num">Low-inc ↑</span>
              <span role="columnheader" className="opt-num">Support</span>
              <span role="columnheader" className="opt-num">Cost*</span>
            </div>
            {result.pareto_front.map((c) => (
              <CandidateRow key={c.policy_id} c={c} />
            ))}
          </div>

          <p className="hint opt-cost-note">
            *Cost is an <span className="tag estimated">Estimated</span> documented proxy for the
            budget constraint — not a simulated outcome (SPEC §22/§34).
          </p>
          <p className="hint opt-note">{result.note}</p>
        </div>
      )}
    </section>
  );
}

function CandidateRow({ c }: { c: OptimiserCandidate }) {
  const m = c.metrics;
  return (
    <div className="opt-row" role="row">
      <span role="cell" className="opt-cand">
        <span className="opt-cand-name" title={c.description.join("; ")}>
          {c.label}
        </span>
      </span>
      <span role="cell" className="opt-num good">{pct(m.emissions_reduction_pct)}</span>
      <span role="cell" className="opt-num good">{pct(m.traffic_reduction_pct)}</span>
      <span role="cell" className="opt-num">{pct(m.avg_commute_increase_pct)}</span>
      <span role="cell" className="opt-num">{pct(m.low_income_burden_pct)}</span>
      <span
        role="cell"
        className={`opt-num ${m.net_support >= 0 ? "good" : "bad"}`}
        title="Modelled net public support in [-1, 1]"
      >
        {m.net_support >= 0 ? "+" : ""}
        {m.net_support.toFixed(2)}
      </span>
      <span role="cell" className="opt-num opt-cost">{money(m.est_cost)}</span>
    </div>
  );
}
