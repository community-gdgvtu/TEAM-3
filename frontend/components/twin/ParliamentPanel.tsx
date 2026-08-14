"use client";

/**
 * Model Parliament view (SPEC §11/§27): convenes the adversarial debate on the
 * compiled policy and renders each persona's evidence-grounded argument with its
 * citations. Debate prose is Generated; every cited number is a Simulated metric
 * or a ledger event (SPEC §34) — surfaced as citation chips so nothing is taken
 * on trust.
 */

import { useEffect, useState } from "react";
import type { FormEvent } from "react";

import {
  PERSONAS,
  amendPolicy,
  applyAmendment,
  askPersona,
  runDebate,
  simulate,
} from "../../lib/api";
import type {
  Amendment,
  AmendmentComparison,
  Argument,
  AskResponse,
  DebateResponse,
  DeltaSeries,
  PersonaName,
  PolicyDSL,
  Stance,
} from "../../lib/api";
import { formatNumber } from "../../lib/format";
import { useTwin } from "./TwinStore";

/** Preset opposition/committee amendments (mirror backend Amendment fields). */
const PRESET_AMENDMENTS: Amendment[] = [
  { label: "Exempt low-income commuters", exempt_low_income: true },
  { label: "Exempt in-cordon residents", exempt_residents: true },
  { label: "Raise the charge ×1.5", charge_multiplier: 1.5 },
  { label: "Reinvest 90% of revenue in transit", set_public_transport_share: 0.9 },
];

const STANCE_LABEL: Record<Stance, string> = {
  support: "Support",
  oppose: "Oppose",
  conditional: "Conditional",
  challenge: "Challenge",
};

type Status = "idle" | "loading" | "ready" | "error";

export default function ParliamentPanel() {
  const { policy, setSim } = useTwin();
  const [status, setStatus] = useState<Status>("idle");
  const [debate, setDebate] = useState<DebateResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [applying, setApplying] = useState<string | null>(null);
  const [amendError, setAmendError] = useState<string | null>(null);
  const [effect, setEffect] = useState<AmendmentComparison | null>(null);

  async function applyAndResimulate(amendment: Amendment) {
    if (!policy) return;
    setApplying(amendment.label);
    setAmendError(null);
    try {
      // Two complementary calls run together:
      //  1. applyAmendment + /simulate → the amended World B drives the shared
      //     map + dashboard (the killer interaction, SPEC §29);
      //  2. /simulate/amend → the server-authoritative isolated Δ(amended −
      //     original), the amendment's own marginal effect (SPEC §12) that the
      //     World-B snapshot alone can't show. Both share the deterministic model.
      const amended = applyAmendment(policy, amendment);
      const [result, comparison] = await Promise.all([
        simulate(amended),
        amendPolicy(policy, amendment),
      ]);
      setSim(result, { label: amendment.label, amended: true });
      setEffect(comparison);
    } catch (e: unknown) {
      setAmendError(e instanceof Error ? e.message : "Re-simulation failed");
    } finally {
      setApplying(null);
    }
  }

  // A new/edited policy invalidates a stale debate and amendment effect.
  useEffect(() => {
    setDebate(null);
    setStatus("idle");
    setError(null);
    setEffect(null);
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

          <AskPersona policy={policy} />

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

          <div className="amendments">
            <h3 className="assumptions-title">Amendment queue</h3>
            <p className="hint" style={{ marginTop: 0 }}>
              Apply an amendment and re-simulate — the outcomes dashboard above
              updates with the amended World B vs baseline (SPEC §29).
            </p>
            <div className="amendment-list">
              {PRESET_AMENDMENTS.map((a) => (
                <button
                  key={a.label}
                  type="button"
                  className="btn amendment-btn"
                  onClick={() => applyAndResimulate(a)}
                  disabled={applying !== null}
                >
                  {applying === a.label
                    ? "Re-simulating…"
                    : `Apply + re-simulate: ${a.label}`}
                </button>
              ))}
            </div>
            {amendError && (
              <p className="hint error-text">Couldn’t re-simulate: {amendError}</p>
            )}

            {effect && <AmendmentEffect effect={effect} />}
          </div>
        </>
      )}
    </section>
  );
}

/**
 * The isolated Δ(amended − original) from `POST /simulate/amend` (SPEC §12): what
 * the amendment itself changes, holding everything else fixed. This is distinct
 * from the dashboard above (which shows the amended World B vs baseline) — here
 * the "before" is the *original policy*, so a near-zero row means the amendment
 * barely moves that metric. Quoted at the final checkpoint; every number Simulated.
 */
function AmendmentEffect({ effect }: { effect: AmendmentComparison }) {
  const series = effect.amendment_delta.series;
  const checkpoints = effect.amendment_delta.checkpoints;
  const horizon = checkpoints[checkpoints.length - 1];
  // Last point of each series = the amendment's effect at the final horizon.
  const rows = series
    .map((s: DeltaSeries) => ({ s, p: s.points[s.points.length - 1] }))
    .filter((r) => r.p != null);

  return (
    <div className="amd-effect">
      <div className="amd-effect-head">
        <span className="tag simulated">Simulated</span>
        <h4>Amendment effect vs original policy</h4>
      </div>
      <p className="hint" style={{ marginTop: 0 }}>
        Δ(amended − original) — the amendment&rsquo;s own marginal effect, isolated
        by re-simulating both policies against the same baseline (SPEC §12).
        {horizon ? ` Quoted at ${horizon.label}.` : ""}
      </p>

      {effect.changes.length > 0 && (
        <ul className="amd-changes">
          {effect.changes.map((c, i) => (
            <li key={i}>{c}</li>
          ))}
        </ul>
      )}

      <div className="amd-table" role="table" aria-label="Amendment effect by metric">
        <div className="amd-row amd-row-head" role="row">
          <span role="columnheader">Metric</span>
          <span role="columnheader" className="amd-num">
            Δ(amended − original)
          </span>
          <span role="columnheader" className="amd-band">
            band
          </span>
        </div>
        {rows.map(({ s, p }) => {
          const dir = p.delta > 0 ? "up" : p.delta < 0 ? "down" : "flat";
          const negligible = Math.abs(p.delta) < 1e-9;
          return (
            <div className="amd-row" role="row" key={s.key}>
              <span role="cell" className="amd-metric">
                <span className="amd-metric-label" title={s.key}>
                  {s.label}
                </span>
                {s.unit && <span className="amd-metric-unit">{s.unit}</span>}
              </span>
              <span role="cell" className={`amd-num ${dir}`}>
                {negligible ? (
                  <span className="amd-flat">≈ 0 (no change)</span>
                ) : (
                  <>
                    <span className="amd-arrow" aria-hidden>
                      {p.delta > 0 ? "▲" : "▼"}
                    </span>{" "}
                    {p.delta > 0 ? "+" : ""}
                    {formatNumber(p.delta)}
                    {p.delta_pct != null
                      ? ` (${p.delta_pct > 0 ? "+" : ""}${p.delta_pct.toFixed(1)}%)`
                      : ""}
                  </>
                )}
              </span>
              <span role="cell" className="amd-band">
                {formatNumber(p.low)} … {formatNumber(p.high)}
              </span>
            </div>
          );
        })}
      </div>
      <p className="hint amd-note">{effect.amendment_delta.note}</p>
    </div>
  );
}

/**
 * Direct follow-up questions to one persona (SPEC §11/§34): calls
 * `POST /parliament/ask`, which reruns the same deterministic simulation as
 * the debate above and answers only from that persona's own evidence points —
 * LLM-phrased when the backend has a key configured, keyword-matched
 * templated prose otherwise. Independent of whether the debate has been
 * convened, since each question computes its own brief.
 */
function AskPersona({ policy }: { policy: PolicyDSL }) {
  const [persona, setPersona] = useState<PersonaName>("Government");
  const [question, setQuestion] = useState("");
  const [thread, setThread] = useState<AskResponse[]>([]);
  const [asking, setAsking] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: FormEvent) {
    e.preventDefault();
    const q = question.trim();
    if (!q) return;
    setAsking(true);
    setError(null);
    try {
      const res = await askPersona(policy, persona, q);
      setThread((t) => [...t, res]);
      setQuestion("");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Couldn't get an answer");
    } finally {
      setAsking(false);
    }
  }

  return (
    <div className="ask-persona">
      <h3 className="assumptions-title">Ask a persona</h3>
      <p className="hint" style={{ marginTop: 0 }}>
        Put a direct question to one member of the chamber — answered from
        their own evidence, never a new number (SPEC §34).
      </p>
      <form className="ask-form" onSubmit={submit}>
        <select
          className="ask-select"
          value={persona}
          onChange={(e) => setPersona(e.target.value as PersonaName)}
          aria-label="Persona to ask"
        >
          {PERSONAS.map((p) => (
            <option key={p} value={p}>
              {p}
            </option>
          ))}
        </select>
        <input
          type="text"
          className="ask-input"
          placeholder="e.g. Who actually pays this charge?"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          maxLength={500}
          aria-label="Question"
        />
        <button
          type="submit"
          className="btn primary"
          disabled={asking || !question.trim()}
        >
          {asking ? "Asking…" : "Ask"}
        </button>
      </form>

      {error && <p className="hint error-text">{error}</p>}

      {thread.length > 0 && (
        <div className="ask-thread">
          {thread.map((a, i) => (
            <div className="ask-exchange" key={i}>
              <p className="ask-question">
                <span className="ask-question-label">Q</span> {a.question}
              </p>
              <div className="ask-answer">
                <div className="ask-answer-head">
                  <span className="argument-persona">{a.persona}</span>
                  <span className="argument-role"> · {a.role}</span>
                  <span className={`stance-chip ${a.stance}`}>
                    {STANCE_LABEL[a.stance]}
                  </span>
                </div>
                <p>{a.answer}</p>
                <span className="tag muted">
                  {a.method === "llm" ? "LLM prose" : "Template prose"}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
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
