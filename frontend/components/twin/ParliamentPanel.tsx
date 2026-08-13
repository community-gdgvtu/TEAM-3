"use client";

/**
 * Model Parliament view (SPEC §11/§27): convenes the adversarial debate on the
 * compiled policy and renders each persona's evidence-grounded argument with its
 * citations. Debate prose is Generated; every cited number is a Simulated metric
 * or a ledger event (SPEC §34) — surfaced as citation chips so nothing is taken
 * on trust.
 */

import { useEffect, useState } from "react";

import { runDebate } from "../../lib/api";
import type { Argument, DebateResponse, Stance } from "../../lib/api";
import { useTwin } from "./TwinStore";

const STANCE_LABEL: Record<Stance, string> = {
  support: "Support",
  oppose: "Oppose",
  conditional: "Conditional",
  challenge: "Challenge",
};

type Status = "idle" | "loading" | "ready" | "error";

export default function ParliamentPanel() {
  const { policy } = useTwin();
  const [status, setStatus] = useState<Status>("idle");
  const [debate, setDebate] = useState<DebateResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  // A new/edited policy invalidates a stale debate.
  useEffect(() => {
    setDebate(null);
    setStatus("idle");
    setError(null);
  }, [policy]);

  async function convene() {
    if (!policy) return;
    setStatus("loading");
    setError(null);
    try {
      const d = await runDebate(policy);
      setDebate(d);
      setStatus("ready");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Debate failed");
      setStatus("error");
    }
  }

  return (
    <section className="card parliament">
      <div className="dashboard-head">
        <h2>Model Parliament</h2>
        <span className="dashboard-sub">
          Adversarial stress test · prose Generated, every figure Simulated
        </span>
      </div>

      {!policy ? (
        <div className="waiting">
          <span className="tag muted">No policy yet</span>
          <p>Compile a policy above to convene the chamber.</p>
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
                ? "Convening…"
                : debate
                  ? "Re-run debate"
                  : "Convene parliament"}
            </button>
            {debate && (
              <span className="tag muted">
                {debate.method === "llm" ? "LLM prose" : "Template prose"}
              </span>
            )}
          </div>

          {status === "error" && (
            <p className="hint error-text">Couldn’t debate: {error}</p>
          )}

          {debate && status === "ready" && (
            <div className="debate">
              <p className="motion">
                <span className="motion-label">Motion</span> {debate.motion}
              </p>

              <Tally tally={debate.tally} />

              <div className="arguments">
                {debate.arguments.map((a) => (
                  <ArgumentCard key={a.persona} arg={a} />
                ))}
              </div>

              <div className="debate-summary">
                <span className="tag generated">Synthesis</span>
                <p>{debate.summary}</p>
              </div>
            </div>
          )}
        </>
      )}
    </section>
  );
}

function Tally({ tally }: { tally: Record<string, number> }) {
  const order: Stance[] = ["support", "conditional", "challenge", "oppose"];
  const entries = order.filter((s) => (tally[s] ?? 0) > 0);
  if (entries.length === 0) return null;
  return (
    <div className="tally">
      {entries.map((s) => (
        <span key={s} className={`stance-chip ${s}`}>
          {tally[s]} {STANCE_LABEL[s]}
        </span>
      ))}
    </div>
  );
}

function ArgumentCard({ arg }: { arg: Argument }) {
  return (
    <div className="argument">
      <div className="argument-head">
        <div>
          <span className="argument-persona">{arg.persona}</span>
          <span className="argument-role"> · {arg.role}</span>
        </div>
        <span className={`stance-chip ${arg.stance}`}>
          {STANCE_LABEL[arg.stance]}
        </span>
      </div>

      <p className="argument-headline">{arg.headline}</p>

      {arg.speech && <p className="argument-speech">{arg.speech}</p>}

      {arg.points.length > 0 && (
        <ul className="argument-points">
          {arg.points.map((p, i) => (
            <li key={i}>{p}</li>
          ))}
        </ul>
      )}

      {arg.citations.length > 0 && (
        <div className="citations">
          {arg.citations.map((c, i) => (
            <span
              key={i}
              className="citation"
              title={`${c.kind}: ${c.ref} (${c.tag})`}
            >
              <span className="citation-kind">{c.kind}</span>
              <span className="citation-detail">{c.detail}</span>
            </span>
          ))}
        </div>
      )}

      <div className="argument-foot">
        <span className="conf-label">confidence</span>
        <span className="conf-bar" aria-hidden>
          <span
            className="conf-fill"
            style={{ width: `${Math.round(arg.confidence * 100)}%` }}
          />
        </span>
        <span className="conf-val">{Math.round(arg.confidence * 100)}%</span>
      </div>
    </div>
  );
}
