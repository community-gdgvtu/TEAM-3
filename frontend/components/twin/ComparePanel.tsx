"use client";

/**
 * Counterfactual comparison view (SPEC §21): World A (baseline) vs World B
 * (intervention) vs one world per amendment (C, D…), all from the same
 * deterministic model via `POST /compare`. The user toggles a small set of
 * structured amendments to spin up extra worlds, then the panel renders the
 * headline table — every metric's baseline value plus each world's value and its
 * Δ-vs-baseline at one horizon.
 *
 * Honesty (SPEC §21/§34): the baseline (World A) is always present and never
 * omitted; every number is Simulated from the model; Δ = world − baseline. Amend-
 * ments are transparent structured edits, not free-text. When the backend is down
 * we show a waiting state instead of inventing a comparison.
 */

import { useEffect, useState } from "react";

import { runCompare } from "../../lib/api";
import type {
  Amendment,
  ComparisonRow,
  CounterfactualComparison,
  CounterfactualWorld,
} from "../../lib/api";
import { formatNumber } from "../../lib/format";
import { useTwin } from "./TwinStore";

type Status = "idle" | "loading" | "ready" | "error";

/** Preset structured amendments the user can toggle into extra worlds. */
const PRESETS: Array<{ key: string; label: string; amendment: Amendment }> = [
  {
    key: "exempt_low_income",
    label: "Exempt low-income",
    amendment: { label: "Exempt low-income", exempt_low_income: true },
  },
  {
    key: "exempt_residents",
    label: "Exempt residents",
    amendment: { label: "Exempt residents", exempt_residents: true },
  },
  {
    key: "charge_up",
    label: "+50% charge",
    amendment: { label: "+50% charge", charge_multiplier: 1.5 },
  },
];

export default function ComparePanel() {
  const { policy } = useTwin();
  const [status, setStatus] = useState<Status>("idle");
  const [result, setResult] = useState<CounterfactualComparison | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<Set<string>>(new Set());

  // A fresh/edited policy invalidates any prior comparison.
  useEffect(() => {
    setResult(null);
    setStatus("idle");
    setError(null);
  }, [policy]);

  function toggle(key: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }

  async function compare() {
    if (!policy) return;
    setStatus("loading");
    setError(null);
    const amendments = PRESETS.filter((p) => selected.has(p.key)).map((p) => p.amendment);
    try {
      const r = await runCompare(policy, amendments);
      setResult(r);
      setStatus("ready");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Comparison failed");
      setStatus("error");
    }
  }

  return (
    <section className="card compare">
      <div className="dashboard-head">
        <h2>Counterfactual worlds</h2>
        <span className="dashboard-sub">
          World A baseline vs B intervention vs amendments (SPEC §21)
        </span>
      </div>

      {!policy ? (
        <div className="waiting">
          <span className="tag muted">No policy yet</span>
          <p>
            Compile a policy above to compare the baseline against the intervention
            and any amendment worlds side by side.
          </p>
        </div>
      ) : (
        <>
          <div className="cmp-presets">
            <span className="cmp-presets-label">Add amendment worlds:</span>
            {PRESETS.map((p) => (
              <label key={p.key} className="cmp-preset">
                <input
                  type="checkbox"
                  checked={selected.has(p.key)}
                  onChange={() => toggle(p.key)}
                />
                {p.label}
              </label>
            ))}
          </div>

          <div className="policy-actions" style={{ marginTop: "0.5rem" }}>
            <button
              type="button"
              className="btn primary"
              onClick={compare}
              disabled={status === "loading"}
            >
              {status === "loading"
                ? "Simulating worlds…"
                : result
                  ? "Re-compare"
                  : "Compare worlds"}
            </button>
            {result && <span className="tag simulated">Simulated</span>}
          </div>

          {status === "error" && (
            <p className="hint error-text">Couldn&rsquo;t compare: {error}</p>
          )}

          {result && status !== "loading" && (
            <div className="cmp-body">
              <div className="cmp-worlds">
                <span className="cmp-world base" title="Always present (SPEC §21)">
                  A · Baseline
                </span>
                {result.worlds.map((w) => (
                  <WorldChip key={w.id} w={w} />
                ))}
              </div>

              <p className="cmp-horizon">Headline table quoted at {result.horizon.label}</p>

              <div
                className="cmp-table"
                role="table"
                aria-label="Metric by world at the headline horizon"
                style={{ ["--cols" as string]: result.worlds.length }}
              >
                <div className="cmp-row cmp-row-head" role="row">
                  <span role="columnheader">Metric</span>
                  <span role="columnheader" className="cmp-num">
                    A · Baseline
                  </span>
                  {result.worlds.map((w) => (
                    <span role="columnheader" className="cmp-num" key={w.id}>
                      {w.id} · {w.label}
                    </span>
                  ))}
                </div>
                {result.headline_table.map((row) => (
                  <MetricRow key={row.key} row={row} worlds={result.worlds} />
                ))}
              </div>

              <p className="hint cmp-note">{result.note}</p>
            </div>
          )}
        </>
      )}
    </section>
  );
}

function WorldChip({ w }: { w: CounterfactualWorld }) {
  return (
    <span className={`cmp-world ${w.role}`} title={w.changes.join("; ") || w.label}>
      {w.id} · {w.label}
      {w.changes.length > 0 && <span className="cmp-world-changes">{w.changes.length} edit(s)</span>}
    </span>
  );
}

function MetricRow({ row, worlds }: { row: ComparisonRow; worlds: CounterfactualWorld[] }) {
  // Cells come keyed by world_id; index them so column order follows `worlds`.
  const byWorld = new Map(row.cells.map((c) => [c.world_id, c]));
  return (
    <div className="cmp-row" role="row">
      <span role="cell" className="cmp-metric">
        <span className="cmp-metric-label" title={row.key}>
          {row.label}
        </span>
        {row.unit && <span className="cmp-metric-unit">{row.unit}</span>}
      </span>
      <span role="cell" className="cmp-num cmp-baseline">
        {formatNumber(row.baseline_value)}
      </span>
      {worlds.map((w) => {
        const cell = byWorld.get(w.id);
        if (!cell) {
          return (
            <span role="cell" className="cmp-num" key={w.id}>
              —
            </span>
          );
        }
        const d = cell.delta_vs_baseline;
        const dir = d > 0 ? "up" : d < 0 ? "down" : "flat";
        return (
          <span role="cell" className="cmp-num" key={w.id}>
            <span className="cmp-val">{formatNumber(cell.value)}</span>
            <span className={`cmp-delta ${dir}`}>
              {d > 0 ? "▲" : d < 0 ? "▼" : "—"} {d > 0 ? "+" : ""}
              {formatNumber(d)}
              {cell.delta_pct != null ? ` (${cell.delta_pct > 0 ? "+" : ""}${cell.delta_pct.toFixed(1)}%)` : ""}
            </span>
          </span>
        );
      })}
    </div>
  );
}
