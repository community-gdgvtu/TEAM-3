"use client";

/**
 * Press conference view (SPEC §16): stages a simulated post-announcement press
 * conference for the compiled policy via `POST /press-conference` — a spokesperson
 * opening statement and five archetype journalist exchanges (public broadcaster,
 * business press, tabloid, environmental, opposition-local), each grounded in a
 * specific Δ metric or event copied from the deterministic simulation.
 *
 * Honesty (SPEC §16/§34): the entire conference is FICTIONAL and stamped
 * SIMULATED — outlets and reporters are invented, never real names. The prose is
 * Generated over Simulated figures; an LLM may polish wording but never produces a
 * number. When the backend is down we show a waiting state, not a fake presser.
 */

import { useEffect, useState } from "react";

import { runPressConference } from "../../lib/api";
import type { PressConference, PressExchange } from "../../lib/api";
import { useTwin } from "./TwinStore";

type Status = "idle" | "loading" | "ready" | "error";

const HOSTILITY_CLASS: Record<string, string> = {
  friendly: "friendly",
  neutral: "neutral",
  hostile: "hostile",
};

const ARCHETYPE_LABEL: Record<string, string> = {
  public_broadcaster: "Public broadcaster",
  business_press: "Business press",
  tabloid: "Tabloid",
  environmental: "Environmental",
  opposition_local: "Opposition-local",
};

export default function PressConferencePanel() {
  const { policy } = useTwin();
  const [status, setStatus] = useState<Status>("idle");
  const [conf, setConf] = useState<PressConference | null>(null);
  const [error, setError] = useState<string | null>(null);

  // A fresh/edited policy invalidates any prior conference.
  useEffect(() => {
    setConf(null);
    setStatus("idle");
    setError(null);
  }, [policy]);

  async function stage() {
    if (!policy) return;
    setStatus("loading");
    setError(null);
    try {
      const c = await runPressConference(policy);
      setConf(c);
      setStatus("ready");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Press conference failed");
      setStatus("error");
    }
  }

  return (
    <section className="card presser">
      <div className="dashboard-head">
        <h2>Press conference</h2>
        <span className="dashboard-sub">
          Simulated post-announcement Q&amp;A · 5 archetype journalists (SPEC §16)
        </span>
      </div>

      {!policy ? (
        <div className="waiting">
          <span className="tag muted">No policy yet</span>
          <p>
            Compile a policy above to stage a simulated press conference — a
            spokesperson faces five archetype journalists, each armed with a model
            figure.
          </p>
        </div>
      ) : (
        <>
          <div className="policy-actions" style={{ marginTop: 0 }}>
            <button
              type="button"
              className="btn primary"
              onClick={stage}
              disabled={status === "loading"}
            >
              {status === "loading"
                ? "Staging conference…"
                : conf
                  ? "Re-run conference"
                  : "Stage press conference"}
            </button>
            {conf && <span className="tag simulated">SIMULATED</span>}
          </div>

          {status === "error" && (
            <p className="hint error-text">Couldn&rsquo;t stage conference: {error}</p>
          )}

          {status === "idle" && !conf && (
            <p className="hint">
              Fictional outlets and reporters only; every question and answer is
              anchored to a Simulated model figure. Click to run.
            </p>
          )}

          {conf && status !== "loading" && (
            <div className="presser-body">
              <div className="presser-disclaimer" role="note">
                <span className="tag simulated">SIMULATED</span>
                <span>{conf.disclaimer}</span>
              </div>

              <div className="presser-head">
                <span className="presser-when">at {conf.horizon.label}</span>
                <span className="presser-mood">Room: {conf.public_mood}</span>
                <span className="presser-method" title="How the prose was rendered">
                  prose: {conf.method === "llm" ? "LLM-polished" : "template"}
                </span>
              </div>

              <div className="presser-opening">
                <span className="presser-speaker">{conf.spokesperson}</span>
                <p className="presser-statement">{conf.opening_statement}</p>
                {conf.opening_refs.length > 0 && (
                  <RefList refs={conf.opening_refs} />
                )}
              </div>

              <ol className="presser-exchanges">
                {conf.exchanges.map((x, i) => (
                  <ExchangeItem key={i} x={x} />
                ))}
              </ol>

              <p className="hint presser-note">{conf.note}</p>
            </div>
          )}
        </>
      )}
    </section>
  );
}

function ExchangeItem({ x }: { x: PressExchange }) {
  const q = x.question;
  const a = x.answer;
  const hostility = HOSTILITY_CLASS[q.hostility] ?? "neutral";
  const archetype = ARCHETYPE_LABEL[q.archetype] ?? q.archetype;
  return (
    <li className="presser-exchange">
      <div className="presser-q">
        <div className="presser-q-head">
          <span className="presser-outlet">{q.outlet_label}</span>
          <span className="presser-reporter">{q.reporter}</span>
          <span className={`presser-hostility ${hostility}`}>{q.hostility}</span>
          <span className="presser-archetype">{archetype}</span>
        </div>
        <p className="presser-question">{q.question}</p>
        {q.angle && <p className="presser-angle">angle: {q.angle}</p>}
        {q.cited_refs.length > 0 && <RefList refs={q.cited_refs} />}
      </div>
      <div className="presser-a">
        <div className="presser-a-head">
          <span className="presser-a-speaker">Spokesperson</span>
          <span className={`presser-stance ${a.stance}`}>{a.stance}</span>
        </div>
        <p className="presser-answer">{a.answer}</p>
        {a.cited_refs.length > 0 && <RefList refs={a.cited_refs} />}
      </div>
    </li>
  );
}

/** Grounding refs — every question/answer points at a Simulated model output. */
function RefList({ refs }: { refs: string[] }) {
  return (
    <div className="presser-refs">
      <span className="presser-refs-label">grounded in</span>
      {refs.map((r) => (
        <span className="presser-ref" key={r} title="Metric key / event id from the simulation">
          {r}
        </span>
      ))}
    </div>
  );
}
