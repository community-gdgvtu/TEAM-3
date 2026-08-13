"use client";

/**
 * Historical Analogue / Causal Layer view (SPEC §7.1): estimates the flagship
 * cordon-traffic effect of the compiled policy from *comparable real-world
 * schemes* (London, Stockholm, Singapore, Milan, Gothenburg, Oslo, Ghent,
 * Madrid) rather than from the synthetic-city agent model — a difference-in-
 * differences read per scheme (treated change − background trend) transferred to
 * this policy by an auditable similarity score, pooled into a central estimate +
 * confidence interval, and cross-checked against the agent-based model (SPEC §8).
 *
 * The honesty story this panel tells (SPEC §7.1/§34): each historical outcome is
 * Observed (a real, published effect) but flagged *illustrative/approximate* — a
 * reference figure, not a live causal-inference pipeline over this city's
 * microdata. The *transfer* of those effects to this policy is Estimated. No LLM
 * touches any number. The confidence band widens when the analogues are weak or
 * disagree, and the structural cross-check calls out when the agent-based model
 * predicts a bigger effect than any real scheme ever achieved. When the backend
 * is down the panel shows an honest waiting/error state, never a fake figure.
 */

import { useEffect, useState } from "react";

import { runAnalogues } from "../../lib/api";
import type { AnalogueEstimate, CaseEstimate, StructuralComparison } from "../../lib/api";
import { useTwin } from "./TwinStore";

type Status = "idle" | "loading" | "ready" | "error";

/** Signed percentage, e.g. -30 → "−30.0%". */
function pct(v: number, dp = 1): string {
  const s = v > 0 ? "+" : v < 0 ? "−" : "";
  return `${s}${Math.abs(v).toFixed(dp)}%`;
}

const QUALITY_CLASS: Record<string, string> = {
  strong: "good",
  moderate: "mid",
  weak: "warn",
};

const AGREEMENT_CLASS: Record<string, string> = {
  consistent: "good",
  "moderate gap": "mid",
  "large gap": "warn",
};

export default function AnaloguePanel() {
  const { policy } = useTwin();
  const [status, setStatus] = useState<Status>("idle");
  const [est, setEst] = useState<AnalogueEstimate | null>(null);
  const [error, setError] = useState<string | null>(null);

  // A fresh/edited policy invalidates any prior analogue run.
  useEffect(() => {
    setEst(null);
    setStatus("idle");
    setError(null);
  }, [policy]);

  async function run() {
    if (!policy) return;
    setStatus("loading");
    setError(null);
    try {
      const e = await runAnalogues(policy);
      setEst(e);
      setStatus("ready");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Analogue layer failed");
      setStatus("error");
    }
  }

  return (
    <section className="card analogue-panel">
      <div className="dashboard-head">
        <h2>Historical analogue</h2>
        <span className="dashboard-sub">
          Flagship cordon effect from comparable real-world schemes · DiD transfer (SPEC §7.1)
        </span>
      </div>

      {!policy ? (
        <div className="waiting">
          <span className="tag muted">No policy yet</span>
          <p>
            Compile a policy above to estimate its headline cordon effect from
            eight real congestion-pricing / access-restriction schemes — a
            difference-in-differences read transferred by an auditable similarity
            score, with an empirical sanity check against the agent-based model.
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
                ? "Transferring analogues…"
                : est
                  ? "Re-run analogue layer"
                  : "Run analogue layer"}
            </button>
            {est && <span className="tag estimated">Estimated (transfer)</span>}
          </div>

          {status === "error" && (
            <p className="hint error-text">Couldn&rsquo;t run the analogue layer: {error}</p>
          )}

          {status === "idle" && !est && (
            <p className="hint">
              Reads the flagship effect from real schemes (London, Stockholm,
              Singapore, Milan, Gothenburg, Oslo, Ghent, Madrid) via a trend-
              stripped DiD, transferred to this policy by family / charge / revenue
              / context similarity. Click to run.
            </p>
          )}

          {est && status !== "loading" && <AnalogueBody est={est} />}
        </>
      )}
    </section>
  );
}

function AnalogueBody({ est }: { est: AnalogueEstimate }) {
  const applicable = est.cases.filter((c) => c.applicable);
  const contextOnly = est.cases.filter((c) => !c.applicable);
  const qClass = QUALITY_CLASS[est.analogue_quality] ?? "mid";
  const noPool = applicable.length === 0;

  return (
    <div className="anl-body">
      {/* Headline: central estimate + CI band + quality/transferability. */}
      <div className="anl-metric">
        <div className="anl-head">
          <div className="anl-headline">
            <span className="anl-central">{noPool ? "—" : pct(est.estimated_effect_pct)}</span>
            <span className="anl-label">{est.metric_label}</span>
          </div>
          <div className="anl-head-meta">
            {!noPool && (
              <span className="anl-band">
                CI {pct(est.ci_low_pct)} … {pct(est.ci_high_pct)}
              </span>
            )}
            <span className={`anl-pill ${qClass}`}>{est.analogue_quality} analogue</span>
            <span className="anl-pill neutral">
              transferability {(est.transferability_score * 100).toFixed(0)}%
            </span>
            <span className="tag estimated">Estimated</span>
          </div>
        </div>

        {noPool ? (
          <p className="anl-interp warn-text">
            No comparable real-world scheme for a{" "}
            {est.intervention_family.replace(/_/g, " ")} policy in the analogue
            base — the causal layer can&rsquo;t transfer an effect here. Rely on
            the structural model instead.
          </p>
        ) : (
          <p className="anl-interp">
            Pooled from {applicable.length} comparable scheme
            {applicable.length === 1 ? "" : "s"} by identification-weighted
            transferability. The band widens when the analogues are weak or
            disagree — it is empirical spread, not false precision.
          </p>
        )}

        {!noPool && <DidChart est={est} applicable={applicable} />}
      </div>

      {/* Structural cross-check (SPEC §8). */}
      {est.structural_comparison && (
        <StructuralCard sc={est.structural_comparison} horizon={est.horizon_label} />
      )}

      {/* Contributing cases: applicable (pooled) then context-only. */}
      <div className="anl-cases">
        <h3 className="anl-h3">
          Analogue base <span className="anl-h3-sub">DiD = treated change − background trend</span>
        </h3>
        <div className="anl-case-table" role="table" aria-label="Historical analogue cases">
          <div className="anl-case-row anl-case-headrow" role="row">
            <span role="columnheader">Scheme</span>
            <span role="columnheader">DiD effect</span>
            <span role="columnheader">Identification</span>
            <span role="columnheader">Transfer</span>
            <span role="columnheader">Weight</span>
          </div>
          {applicable.map((c) => (
            <CaseRow key={c.case_id} c={c} pooled />
          ))}
          {contextOnly.map((c) => (
            <CaseRow key={c.case_id} c={c} pooled={false} />
          ))}
        </div>
        {contextOnly.length > 0 && (
          <p className="hint anl-context-note">
            {contextOnly.length} scheme{contextOnly.length === 1 ? "" : "s"} use a
            different mechanism to this policy — shown for context, not pooled
            (weight 0).
          </p>
        )}
      </div>

      {/* Identification / parallel-trend diagnostics (SPEC §7.1). */}
      {est.identification_diagnostics.length > 0 && (
        <div className="anl-diag">
          <h3 className="anl-h3">Identification diagnostics</h3>
          <ul className="anl-diag-list">
            {est.identification_diagnostics.map((d, i) => (
              <li key={i}>{d}</li>
            ))}
          </ul>
        </div>
      )}

      {/* What this layer does NOT model (SPEC §34 honesty surface). */}
      {est.not_modelled.length > 0 && (
        <details className="anl-notmodelled">
          <summary>What this layer does not model ({est.not_modelled.length})</summary>
          <ul>
            {est.not_modelled.map((n, i) => (
              <li key={i}>{n}</li>
            ))}
          </ul>
        </details>
      )}

      <p className="hint anl-note">{est.note}</p>
    </div>
  );
}

/**
 * Horizontal DiD scale: each pooled case's effect as a marker sized by weight,
 * with the pooled central estimate + confidence band drawn as a highlighted span
 * behind them. Shares one linear scale so the reader sees the real spread.
 */
function DidChart({ est, applicable }: { est: AnalogueEstimate; applicable: CaseEstimate[] }) {
  const effects = applicable.map((c) => c.did_effect_pct);
  let lo = Math.min(...effects, est.ci_low_pct, 0);
  let hi = Math.max(...effects, est.ci_high_pct, 0);
  if (hi - lo < 1e-6) {
    lo -= 1;
    hi += 1;
  }
  const pad = (hi - lo) * 0.06;
  lo -= pad;
  hi += pad;
  const span = hi - lo;
  const xf = (v: number) => ((v - lo) / span) * 100;

  return (
    <div className="anl-chart">
      <div className="anl-scale">
        <span>{pct(lo, 0)}</span>
        {lo < 0 && hi > 0 && (
          <span className="anl-zero-label" style={{ left: `${xf(0)}%` }}>
            0
          </span>
        )}
        <span>{pct(hi, 0)}</span>
      </div>
      <div
        className="anl-plot"
        role="img"
        aria-label={`Difference-in-differences effects across ${applicable.length} comparable schemes; pooled estimate ${pct(
          est.estimated_effect_pct,
        )}, confidence interval ${pct(est.ci_low_pct)} to ${pct(est.ci_high_pct)}.`}
      >
        {/* Pooled confidence band + central line. */}
        <div
          className="anl-cband"
          style={{
            left: `${xf(est.ci_low_pct)}%`,
            width: `${Math.max(xf(est.ci_high_pct) - xf(est.ci_low_pct), 0.5)}%`,
          }}
          title={`Confidence interval ${pct(est.ci_low_pct)} … ${pct(est.ci_high_pct)}`}
        />
        <div className="anl-ccentral" style={{ left: `${xf(est.estimated_effect_pct)}%` }} />
        {lo < 0 && hi > 0 && <div className="anl-zeroline" style={{ left: `${xf(0)}%` }} />}

        {applicable.map((c) => (
          <div
            key={c.case_id}
            className="anl-cmarker"
            style={{
              left: `${xf(c.did_effect_pct)}%`,
              // Marker weight scales with pool weight so heavy cases read louder.
              opacity: 0.45 + Math.min(c.pool_weight, 1) * 0.55,
            }}
            title={`${c.name} (${c.year}): DiD ${pct(c.did_effect_pct)}, weight ${(
              c.pool_weight * 100
            ).toFixed(0)}%`}
          />
        ))}
      </div>
      <div className="anl-chart-legend">
        <span>
          <i className="anl-swatch band" /> pooled CI
        </span>
        <span>
          <i className="anl-swatch central" /> central {pct(est.estimated_effect_pct)}
        </span>
        <span>
          <i className="anl-swatch marker" /> each scheme (opacity = weight)
        </span>
      </div>
    </div>
  );
}

function StructuralCard({ sc, horizon }: { sc: StructuralComparison; horizon: string }) {
  const aClass = AGREEMENT_CLASS[sc.agreement] ?? "mid";
  return (
    <div className="anl-struct">
      <div className="anl-struct-head">
        <h3 className="anl-h3">Cross-check vs agent-based model</h3>
        <span className={`anl-pill ${aClass}`}>{sc.agreement}</span>
      </div>
      <div className="anl-struct-grid">
        <div className="anl-struct-cell">
          <span className="anl-struct-val">{pct(sc.structural_effect_pct)}</span>
          <span className="anl-struct-cap">
            structural model <span className="tag simulated">Simulated</span>
          </span>
        </div>
        <div className="anl-struct-cell">
          <span className="anl-struct-val">{pct(sc.analogue_effect_pct)}</span>
          <span className="anl-struct-cap">
            analogue layer <span className="tag estimated">Estimated</span>
          </span>
        </div>
        <div className="anl-struct-cell">
          <span className="anl-struct-val">{pct(sc.gap_pct_points, 1)} pts</span>
          <span className="anl-struct-cap">gap (structural − analogue)</span>
        </div>
      </div>
      <p className="anl-struct-interp">{sc.interpretation}</p>
      <p className="hint anl-struct-horizon">
        Compared at the {horizon} checkpoint. The analogue range is an empirical
        sanity floor for the structural magnitude (SPEC §8).
      </p>
    </div>
  );
}

function CaseRow({ c, pooled }: { c: CaseEstimate; pooled: boolean }) {
  return (
    <div className={`anl-case-row${pooled ? "" : " off"}`} role="row">
      <span className="anl-case-name" role="cell">
        <span className="anl-case-title">{c.name}</span>
        <span className="anl-case-year">{c.year}</span>
      </span>
      <span className="anl-case-did" role="cell">
        {pct(c.did_effect_pct, 0)}
      </span>
      <span className="anl-case-id" role="cell">
        {(c.identification_strength * 100).toFixed(0)}%
      </span>
      <span className="anl-case-transfer" role="cell">
        {pooled ? `${(c.transferability_score * 100).toFixed(0)}%` : "—"}
      </span>
      <span className="anl-case-weight" role="cell">
        {pooled ? `${(c.pool_weight * 100).toFixed(0)}%` : "context"}
      </span>
    </div>
  );
}
