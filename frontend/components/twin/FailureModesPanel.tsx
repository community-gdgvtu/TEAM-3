"use client";

/**
 * Failure Mode Register — the Devil's Advocate "Red Team" view (SPEC §12/§27).
 *
 * Convenes `POST /parliament/failure-modes` on the compiled policy and renders
 * the ranked register: each mode carries a severity tier, an estimated
 * probability, the causal mechanism, a concrete mitigation, and the Simulated
 * evidence it rests on.
 *
 * Provenance (SPEC §34): the register itself is an **Estimated** risk overlay —
 * severity and probability are transparent structured judgements — but every
 * cited figure is a Simulated metric or ledger event, surfaced as citation
 * chips so nothing is taken on trust. No fabricated numbers.
 */

import { useEffect, useState } from "react";

import { runFailureModes } from "../../lib/api";
import type {
  EvidenceCitation,
  FailureMode,
  FailureModeRegister,
  Severity,
} from "../../lib/api";
import { useTwin } from "./TwinStore";

const SEVERITY_LABEL: Record<Severity, string> = {
  low: "Low",
  medium: "Medium",
  high: "High",
  critical: "Critical",
};

type Status = "idle" | "loading" | "ready" | "error";

export default function FailureModesPanel() {
  const { policy } = useTwin();
  const [status, setStatus] = useState<Status>("idle");
  const [register, setRegister] = useState<FailureModeRegister | null>(null);
  const [error, setError] = useState<string | null>(null);

  // A new/edited policy invalidates a stale register.
  useEffect(() => {
    setRegister(null);
    setStatus("idle");
    setError(null);
  }, [policy]);

  async function assess() {
    if (!policy) return;
    setStatus("loading");
    setError(null);
    try {
      const r = await runFailureModes(policy);
      setRegister(r);
      setStatus("ready");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Assessment failed");
      setStatus("error");
    }
  }

  return (
    <section className="card redteam">
      <div className="dashboard-head">
        <h2>Failure Mode Register</h2>
        <span className="dashboard-sub">
          Devil&rsquo;s Advocate red team · risk scores Estimated, evidence Simulated
        </span>
      </div>

      {!policy ? (
        <div className="waiting">
          <span className="tag muted">No policy yet</span>
          <p>Compile a policy above to stress-test it for failure modes.</p>
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
                : register
                  ? "Re-assess risks"
                  : "Assess failure modes"}
            </button>
            {register && (
              <span className="tag muted">
                {register.failure_modes.length} mode
                {register.failure_modes.length === 1 ? "" : "s"} · ranked by risk
              </span>
            )}
          </div>

          {status === "error" && (
            <p className="hint error-text">Couldn&rsquo;t assess: {error}</p>
          )}

          {register && status === "ready" && (
            <div className="redteam-body">
              {register.failure_modes.length === 0 ? (
                <div className="waiting" style={{ marginTop: "0.6rem" }}>
                  <span className="tag muted">No modes raised</span>
                  <p>
                    The model output didn&rsquo;t support any failure mode for this
                    policy. A mode is only raised when a Simulated metric or ledger
                    event backs it (SPEC §34).
                  </p>
                </div>
              ) : (
                <>
                  <p className="hint" style={{ marginTop: "0.6rem" }}>
                    {register.note}
                  </p>
                  <ol className="fm-list">
                    {register.failure_modes.map((fm, i) => (
                      <FailureModeCard key={fm.id} fm={fm} rank={i + 1} />
                    ))}
                  </ol>
                </>
              )}
            </div>
          )}
        </>
      )}
    </section>
  );
}

function FailureModeCard({ fm, rank }: { fm: FailureMode; rank: number }) {
  const pct = Math.round(fm.probability * 100);
  return (
    <li className="fm-card">
      <div className="fm-head">
        <div className="fm-title">
          <span className="fm-rank">#{rank}</span>
          <span className="fm-risk">{fm.risk}</span>
        </div>
        <div className="fm-tags">
          <span className={`severity-chip ${fm.severity}`}>
            {SEVERITY_LABEL[fm.severity]}
          </span>
          <span className="fm-score" title="severity weight × probability">
            risk {fm.risk_score.toFixed(2)}
          </span>
        </div>
      </div>

      <div className="fm-prob">
        <span className="fm-prob-label">likelihood</span>
        <span className="fm-prob-bar" aria-hidden>
          <span
            className={`fm-prob-fill ${fm.severity}`}
            style={{ width: `${pct}%` }}
          />
        </span>
        <span className="fm-prob-val">{pct}%</span>
      </div>

      <p className="fm-mechanism">{fm.mechanism}</p>

      <div className="fm-mitigation">
        <span className="fm-mitigation-label">Mitigation</span>
        <p>{fm.mitigation}</p>
      </div>

      {fm.affected_agents > 0 && (
        <p className="fm-affected">
          Exposure: {fm.affected_agents.toLocaleString()} commuters / trips
        </p>
      )}

      {fm.evidence.length > 0 && (
        <div className="citations">
          {fm.evidence.map((c, i) => (
            <Citation key={i} c={c} />
          ))}
        </div>
      )}
    </li>
  );
}

function Citation({ c }: { c: EvidenceCitation }) {
  return (
    <span className="citation" title={`${c.kind}: ${c.ref} (${c.tag})`}>
      <span className="citation-kind">{c.kind}</span>
      <span className="citation-detail">{c.detail}</span>
    </span>
  );
}
