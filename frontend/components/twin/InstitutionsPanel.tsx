"use client";

/**
 * Institutional review view (SPEC §18): four institutional agents — Climate,
 * Implementation, Legal/Constitutional, and Auditor — each assess the compiled
 * policy against a professional mandate via `POST /institutions/review`. Every
 * verdict and cited figure is grounded in the deterministic simulation's Δ
 * metrics and event ledger.
 *
 * Honesty (SPEC §18/§34): the review *prose* is Generated, but no LLM produces a
 * number — every citation points at a Simulated model output and carries its tag.
 * The overall verdict is the single most severe agent verdict (deterministic),
 * never an averaged-away "looks fine". When the backend is down we show a waiting
 * state rather than inventing verdicts.
 */

import { useEffect, useState } from "react";

import { runInstitutions } from "../../lib/api";
import type {
  EvidenceCitation,
  InstitutionalFinding,
  InstitutionalReview,
  InstitutionsResponse,
  Verdict,
} from "../../lib/api";
import { useTwin } from "./TwinStore";

type Status = "idle" | "loading" | "ready" | "error";

const VERDICT_CLASS: Record<Verdict, string> = {
  clear: "clear",
  conditional: "conditional",
  concern: "concern",
  block: "block",
};

const VERDICT_LABEL: Record<Verdict, string> = {
  clear: "Clear to proceed",
  conditional: "Proceed with conditions",
  concern: "Material concerns",
  block: "Should not proceed as drafted",
};

const SEVERITY_CLASS: Record<string, string> = {
  info: "info",
  watch: "watch",
  risk: "risk",
  blocker: "blocker",
};

export default function InstitutionsPanel() {
  const { policy } = useTwin();
  const [status, setStatus] = useState<Status>("idle");
  const [panel, setPanel] = useState<InstitutionsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  // A fresh/edited policy invalidates any prior review.
  useEffect(() => {
    setPanel(null);
    setStatus("idle");
    setError(null);
  }, [policy]);

  async function convene() {
    if (!policy) return;
    setStatus("loading");
    setError(null);
    try {
      const p = await runInstitutions(policy);
      setPanel(p);
      setStatus("ready");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Institutional review failed");
      setStatus("error");
    }
  }

  return (
    <section className="card institutions">
      <div className="dashboard-head">
        <h2>Institutional review</h2>
        <span className="dashboard-sub">
          Climate · Implementation · Legal · Auditor — evidence-grounded verdicts (SPEC §18)
        </span>
      </div>

      {!policy ? (
        <div className="waiting">
          <span className="tag muted">No policy yet</span>
          <p>
            Compile a policy above to convene the institutional review panel — each
            agent judges it against a professional mandate using the simulation.
          </p>
        </div>
      ) : (
        <>
          <div className="policy-actions" style={{ marginTop: 0 }}>
            <button
              type="button"
              className="btn primary"
              onClick={convene}
              disabled={status === "loading"}
            >
              {status === "loading"
                ? "Convening panel…"
                : panel
                  ? "Re-run review"
                  : "Convene review panel"}
            </button>
            {panel && <span className="tag generated">Prose Generated · numbers Simulated</span>}
          </div>

          {status === "error" && (
            <p className="hint error-text">Couldn&rsquo;t run review: {error}</p>
          )}

          {status === "idle" && !panel && (
            <p className="hint">
              Four institutional agents each assess the policy against their
              mandate, citing the model&rsquo;s Δ metrics and events. Click to run.
            </p>
          )}

          {panel && status !== "loading" && (
            <div className="inst-body">
              <OverallBanner panel={panel} />
              <div className="inst-reviews">
                {panel.reviews.map((r) => (
                  <ReviewCard key={r.agent} r={r} />
                ))}
              </div>
              <p className="hint inst-note">{panel.note}</p>
            </div>
          )}
        </>
      )}
    </section>
  );
}

function OverallBanner({ panel }: { panel: InstitutionsResponse }) {
  const v = panel.overall_verdict;
  const order: Verdict[] = ["clear", "conditional", "concern", "block"];
  return (
    <div className={`inst-overall ${VERDICT_CLASS[v]}`}>
      <div className="inst-overall-head">
        <span className="inst-overall-label">Overall</span>
        <span className={`inst-verdict ${VERDICT_CLASS[v]}`}>{VERDICT_LABEL[v]}</span>
        <span className="inst-overall-note">most severe single verdict</span>
      </div>
      <div className="inst-tally">
        {order.map((k) =>
          panel.verdict_tally[k] ? (
            <span key={k} className={`inst-tally-chip ${VERDICT_CLASS[k]}`}>
              {panel.verdict_tally[k]} {k}
            </span>
          ) : null,
        )}
      </div>
      {panel.summary && <p className="inst-overall-summary">{panel.summary}</p>}
    </div>
  );
}

function ReviewCard({ r }: { r: InstitutionalReview }) {
  return (
    <div className={`inst-review ${VERDICT_CLASS[r.verdict]}`}>
      <div className="inst-review-head">
        <div className="inst-agent-block">
          <span className="inst-agent">{r.agent}</span>
          <span className="inst-mandate">{r.mandate}</span>
        </div>
        <div className="inst-review-meta">
          <span className={`inst-verdict ${VERDICT_CLASS[r.verdict]}`}>{r.verdict}</span>
          <span className="inst-confidence" title="Agent confidence">
            {Math.round(r.confidence * 100)}% conf
          </span>
        </div>
      </div>

      <p className="inst-summary">{r.summary}</p>

      {r.findings.length > 0 && (
        <ul className="inst-findings">
          {r.findings.map((f, i) => (
            <FindingRow key={`${f.dimension}-${i}`} f={f} />
          ))}
        </ul>
      )}

      {r.recommendation && (
        <p className="inst-reco">
          <span className="inst-reco-label">Recommendation</span> {r.recommendation}
        </p>
      )}

      {r.citations.length > 0 && (
        <div className="inst-citations">
          {r.citations.map((c, i) => (
            <CitationChip key={`${c.ref}-${i}`} c={c} />
          ))}
        </div>
      )}
    </div>
  );
}

function FindingRow({ f }: { f: InstitutionalFinding }) {
  const sev = SEVERITY_CLASS[f.severity] ?? "info";
  return (
    <li className={`inst-finding ${sev}`}>
      <span className={`inst-sev ${sev}`}>{f.severity}</span>
      <span className="inst-finding-dim">{f.dimension}:</span>{" "}
      <span className="inst-finding-detail">{f.detail}</span>
    </li>
  );
}

function CitationChip({ c }: { c: EvidenceCitation }) {
  return (
    <span className="inst-cite" title={`${c.kind}: ${c.ref}`}>
      <span className="inst-cite-ref">{c.ref}</span>
      <span className="inst-cite-detail">{c.detail}</span>
      <span className={`tag ${c.tag.toLowerCase()}`}>{c.tag}</span>
    </span>
  );
}
