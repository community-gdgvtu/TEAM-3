"use client";

/**
 * SDG alignment view (SPEC §23): maps the deterministic simulation + cohort
 * outcomes onto UN SDG targets via `POST /sdg`. Each goal groups measurable
 * indicators (or transparent proxies), and every indicator carries its own
 * baseline / scenario / change / data-source / confidence.
 *
 * Guardrail (SPEC §23): there is **no composite "SDG score"** — the headline is a
 * count of improved / worsened / unchanged indicators, nothing more. Every number
 * is Simulated (SPEC §34); no LLM is on the numeric path. When the backend is down
 * the panel shows an honest waiting/error state rather than inventing alignment.
 */

import { useEffect, useState } from "react";

import { runSdg } from "../../lib/api";
import type { SdgGoal, SdgIndicator, SdgReport } from "../../lib/api";
import { formatNumber, formatSignedPct } from "../../lib/format";
import { useTwin } from "./TwinStore";

type Status = "idle" | "loading" | "ready" | "error";

export default function SdgPanel() {
  const { policy } = useTwin();
  const [status, setStatus] = useState<Status>("idle");
  const [report, setReport] = useState<SdgReport | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setReport(null);
    setStatus("idle");
    setError(null);
  }, [policy]);

  async function assess() {
    if (!policy) return;
    setStatus("loading");
    setError(null);
    try {
      const r = await runSdg(policy);
      setReport(r);
      setStatus("ready");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "SDG model failed");
      setStatus("error");
    }
  }

  return (
    <section className="card sdg">
      <div className="dashboard-head">
        <h2>SDG alignment</h2>
        <span className="dashboard-sub">
          UN SDG targets · measurable indicators, no composite score (SPEC §23)
        </span>
      </div>

      {!policy ? (
        <div className="waiting">
          <span className="tag muted">No policy yet</span>
          <p>Compile a policy above to map it onto the Sustainable Development Goals.</p>
        </div>
      ) : (
        <>
          <div className="policy-actions" style={{ marginTop: 0 }}>
            <button
              type="button"
              className="btn primary"
              onClick={assess}
              disabled={status === "loading"}
            >
              {status === "loading"
                ? "Assessing…"
                : report
                  ? "Re-assess alignment"
                  : "Assess SDG alignment"}
            </button>
            {report && <span className="tag simulated">Simulated</span>}
          </div>

          {status === "error" && (
            <p className="hint error-text">Couldn&rsquo;t assess alignment: {error}</p>
          )}

          {report && status === "ready" && (
            <div className="sdg-body">
              <div className="sdg-headline">
                <ScoreCount label="Improved" n={report.total_improved} cls="pos" />
                <ScoreCount label="Worsened" n={report.total_worsened} cls="neg" />
                <ScoreCount
                  label="Unchanged"
                  n={report.total_unchanged}
                  cls="flat"
                />
                <span className="sdg-horizon">at {report.horizon.label}</span>
              </div>
              <p className="sdg-headline-note">{report.headline}</p>

              <div className="sdg-goals">
                {report.goals.map((g) => (
                  <GoalCard key={g.goal} goal={g} />
                ))}
              </div>

              <p className="hint sdg-note">{report.note}</p>
            </div>
          )}
        </>
      )}
    </section>
  );
}

function ScoreCount({
  label,
  n,
  cls,
}: {
  label: string;
  n: number;
  cls: "pos" | "neg" | "flat";
}) {
  return (
    <span className={`sdg-count ${cls}`}>
      <span className="sdg-count-n">{n}</span>
      <span className="sdg-count-label">{label}</span>
    </span>
  );
}

function GoalCard({ goal }: { goal: SdgGoal }) {
  return (
    <div className="sdg-goal">
      <div className="sdg-goal-head">
        <span className="sdg-goal-num" aria-hidden>
          SDG {goal.goal}
        </span>
        <span className="sdg-goal-title">{goal.title}</span>
        <span className={`sdg-tier ${goal.tier}`}>{goal.tier}</span>
      </div>
      {goal.summary && <p className="sdg-goal-summary">{goal.summary}</p>}
      <div className="sdg-indicators">
        {goal.indicators.map((ind) => (
          <IndicatorRow key={ind.id} ind={ind} />
        ))}
      </div>
    </div>
  );
}

function IndicatorRow({ ind }: { ind: SdgIndicator }) {
  // Direction-aware: a change toward the target reads positive regardless of sign.
  const dirCls = ind.improved
    ? "pos"
    : ind.change === 0
      ? "flat"
      : "neg";
  const arrow = ind.change > 0 ? "▲" : ind.change < 0 ? "▼" : "→";
  const unit = ind.unit && ind.unit !== "count" ? ` ${ind.unit}` : "";

  return (
    <div className="sdg-ind">
      <div className="sdg-ind-head">
        <span className="sdg-ind-name" title={`Proxy for: ${ind.proxy_for}`}>
          {ind.indicator}
        </span>
        <span className="sdg-ind-target">{ind.sdg_target}</span>
      </div>
      <div className="sdg-ind-nums">
        <span className="sdg-ind-cell">
          <span className="sdg-ind-cell-label">Baseline</span>
          <span className="sdg-ind-cell-val">{formatNumber(ind.baseline)}{unit}</span>
        </span>
        <span className="sdg-ind-cell">
          <span className="sdg-ind-cell-label">Scenario</span>
          <span className="sdg-ind-cell-val">{formatNumber(ind.scenario)}{unit}</span>
        </span>
        <span className={`sdg-ind-change ${dirCls}`}>
          <span aria-hidden>{arrow}</span>{" "}
          {ind.change_pct != null
            ? formatSignedPct(ind.change_pct / 100)
            : formatNumber(ind.change)}
          <span className="sdg-ind-verdict">
            {ind.improved ? "toward target" : ind.change === 0 ? "no change" : "away"}
          </span>
        </span>
      </div>
      <div className="sdg-ind-foot">
        <span className={`conf-chip ${ind.confidence_label}`}>
          {ind.confidence_label} confidence · {Math.round(ind.confidence * 100)}%
        </span>
        <span className="sdg-ind-src">{ind.data_source}</span>
        <span className={`tag ${ind.tag.toLowerCase()}`}>{ind.tag}</span>
      </div>
      {ind.note && <p className="sdg-ind-note">{ind.note}</p>}
    </div>
  );
}
