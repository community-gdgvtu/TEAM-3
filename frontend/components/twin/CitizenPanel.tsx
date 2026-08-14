"use client";

/**
 * Citizen View — follow one household through the Time Machine (SPEC §17/§31).
 *
 * Every other analysis tab aggregates the population; this one drills down to a
 * single synthetic household and shows its before/after life under the policy:
 * its profile, its World-A (no-policy) commute + transport cost, and how both —
 * plus its policy support (the SPEC §31 Agent State) — evolve across the
 * Time-Machine checkpoints, with a deterministic "Why?" narrative.
 *
 * A "click a household" picker (`GET /citizen/sample`, policy-independent) spans
 * the income spectrum; five archetype selectors (representative / most-burdened /
 * biggest-loser / biggest-winner / median) let the judge jump to the household a
 * question is really about. `POST /citizen` then returns that household's staged
 * trajectory.
 *
 * Honesty (SPEC §17/§31/§34): commute / cost / mode reuse the *same*
 * deterministic mode-choice model as `/simulate`; support reuses the *same*
 * per-agent opinion model `/public` aggregates — the far-horizon support equals
 * this agent's contribution to the public tab, so a citizen's numbers can never
 * disagree with the dashboard. No LLM touches the numeric path. The household is
 * a synthetic micro-agent (SPEC §6), never a real person → Simulated. Commute /
 * cost bands widen monotonically with the horizon. Idle / loading / error states
 * are shown honestly when the backend is down — a life is never fabricated.
 */

import { useEffect, useRef, useState } from "react";

import {
  CITIZEN_SELECTORS,
  getCitizenSample,
  runCitizen,
} from "../../lib/api";
import type {
  CitizenSample,
  CitizenSelector,
  CitizenSnapshot,
  CitizenView,
} from "../../lib/api";
import { formatNumber } from "../../lib/format";
import { useTwin } from "./TwinStore";

type Status = "idle" | "loading" | "ready" | "error";

/** Human labels for the archetype selectors. */
const SELECTOR_LABELS: Record<CitizenSelector, string> = {
  representative: "Representative",
  most_burdened: "Most burdened",
  biggest_loser: "Biggest loser",
  biggest_winner: "Biggest winner",
  median: "Median",
};

/** Signed money-ish value with a fixed style. */
function signed(v: number): string {
  return `${v > 0 ? "+" : ""}${formatNumber(v)}`;
}

/** Stance → tone class for support colouring. */
function stanceTone(stance: string): string {
  if (stance === "supports") return "good";
  if (stance === "opposes") return "bad";
  return "neutral";
}

export default function CitizenPanel() {
  const { policy } = useTwin();
  const [status, setStatus] = useState<Status>("idle");
  const [view, setView] = useState<CitizenView | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [selector, setSelector] = useState<CitizenSelector>("representative");
  const [agentId, setAgentId] = useState<string | null>(null);

  const [samples, setSamples] = useState<CitizenSample[]>([]);
  const [sampleErr, setSampleErr] = useState<string | null>(null);
  const loadedSamples = useRef(false);

  // Populate the household picker once (policy-independent, SPEC §17).
  useEffect(() => {
    if (loadedSamples.current) return;
    loadedSamples.current = true;
    getCitizenSample(6)
      .then(setSamples)
      .catch((e: unknown) =>
        setSampleErr(e instanceof Error ? e.message : "Sample unavailable"),
      );
  }, []);

  // A fresh/edited policy invalidates any prior citizen trajectory.
  useEffect(() => {
    setView(null);
    setStatus("idle");
    setError(null);
  }, [policy]);

  async function run(sel: CitizenSelector, id: string | null) {
    if (!policy) return;
    setSelector(sel);
    setAgentId(id);
    setStatus("loading");
    setError(null);
    try {
      const r = await runCitizen(policy, { select: sel, agentId: id });
      setView(r);
      setStatus("ready");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Citizen model failed");
      setStatus("error");
    }
  }

  return (
    <section className="card cit">
      <div className="dashboard-head">
        <h2>Citizen View</h2>
        <span className="dashboard-sub">
          Click a household — one life through the Time Machine (SPEC §17/§31)
        </span>
      </div>

      {!policy ? (
        <div className="waiting">
          <span className="tag muted">No policy yet</span>
          <p>
            Compile a policy above to follow a single household&rsquo;s
            before/after commute, cost and support across the horizon. Every
            number reuses the same deterministic models as the dashboard beside
            it — no LLM on the numeric path.
          </p>
        </div>
      ) : (
        <>
          <p className="hint cit-consistency">
            One synthetic household (SPEC §6) — not a real person. Commute, cost
            and mode reuse the same deterministic mode-choice model as{" "}
            <strong>/simulate</strong>; support reuses the same per-agent opinion
            model <strong>/public</strong> aggregates, so this household&rsquo;s
            far-horizon support equals its contribution to the Public tab. No LLM
            touches the numeric path (SPEC §34).
          </p>

          <div className="cit-controls">
            <div className="cit-selectors" role="group" aria-label="Pick by archetype">
              <span className="run-label">Pick by archetype</span>
              <div className="cit-chiprow">
                {CITIZEN_SELECTORS.map((s) => (
                  <button
                    key={s}
                    type="button"
                    className={`chip cit-chip${
                      status !== "loading" && agentId === null && selector === s
                        ? " active"
                        : ""
                    }`}
                    onClick={() => run(s, null)}
                    disabled={status === "loading"}
                  >
                    {SELECTOR_LABELS[s]}
                  </button>
                ))}
              </div>
            </div>

            {samples.length > 0 && (
              <div className="cit-samples" role="group" aria-label="Click a household">
                <span className="run-label">Or click a household</span>
                <div className="cit-chiprow">
                  {samples.map((c) => (
                    <button
                      key={c.agent_id}
                      type="button"
                      className={`chip cit-chip cit-sample${
                        agentId === c.agent_id ? " active" : ""
                      }`}
                      onClick={() => run(selector, c.agent_id)}
                      disabled={status === "loading"}
                      title={`${c.label} · baseline mode ${c.baseline_mode.replace(
                        "_",
                        " ",
                      )}`}
                    >
                      <span className="cit-sample-id">{c.agent_id}</span>
                      <span className="cit-sample-label">{c.label}</span>
                    </button>
                  ))}
                </div>
              </div>
            )}
            {sampleErr && (
              <p className="hint">
                Household picker unavailable ({sampleErr}) — the archetype
                selectors above still work.
              </p>
            )}
          </div>

          {status === "loading" && (
            <p className="hint">Following this household through the Time Machine…</p>
          )}
          {status === "error" && <p className="hint error-text">{error}</p>}

          {view && status !== "loading" && <CitizenResult v={view} />}
        </>
      )}
    </section>
  );
}

function CitizenResult({ v }: { v: CitizenView }) {
  const p = v.profile;
  const before = v.before_policy;
  const end = v.trajectory[v.trajectory.length - 1] ?? before;

  return (
    <div className="cit-body">
      <p className="cit-headline">{v.headline}</p>
      <p className="cit-meta">
        Selected as <strong>{v.selector}</strong> · policy {v.policy_id} ·{" "}
        <span className="tag simulated">Simulated</span>
      </p>

      {/* Profile card */}
      <div className="cit-profile">
        <div className="cit-profile-head">
          <span className="cit-profile-id">{p.agent_id}</span>
          <span className="tag simulated">Simulated agent</span>
        </div>
        <div className="cit-profile-grid">
          <Fact k="Occupation" val={p.occupation} />
          <Fact k="Income band" val={p.income_band} />
          <Fact k="Monthly income" val={`$${formatNumber(p.income_monthly)}`} />
          <Fact k="Age" val={`${p.age}`} />
          <Fact k="Household size" val={`${p.household_size}`} />
          <Fact k="Home zone" val={p.home_zone} />
          <Fact k="Work zone" val={p.work_zone} />
          <Fact
            k="Commute"
            val={`${formatNumber(p.commute_distance_km)} km${
              p.commutes_into_cbd ? " → CBD" : ""
            }`}
          />
          <Fact k="Car access" val={p.car_access ? "yes" : "no"} />
          <Fact k="Transit access" val={p.public_transit_access ? "yes" : "no"} />
        </div>
        <p className="cit-provenance">{p.provenance}</p>
      </div>

      {/* Before → after topline */}
      <div className="cit-beforeafter">
        <DeltaTile
          label="Commute (one way)"
          unit="min"
          before={before.commute_minutes_one_way}
          after={end.commute_minutes_one_way}
          lowerIsBetter
        />
        <DeltaTile
          label="Transport cost"
          unit="$/mo"
          before={before.monthly_transport_cost}
          after={end.monthly_transport_cost}
          lowerIsBetter
        />
        <SupportTile snap={end} />
      </div>

      {/* Trajectory through the Time Machine */}
      <h3 className="cit-sub">Through the Time Machine</h3>
      <p className="cit-sub-note">
        World-A (no policy) reference, then this household&rsquo;s experience at
        each checkpoint. Commute &amp; cost bands widen with the horizon
        (SPEC §9/§34).
      </p>
      <TrajectoryTable before={before} trajectory={v.trajectory} />

      {/* Why? narrative */}
      {v.explanation.length > 0 && (
        <>
          <h3 className="cit-sub">Why?</h3>
          <ol className="cit-why">
            {v.explanation.map((line, i) => (
              <li key={i}>{line}</li>
            ))}
          </ol>
        </>
      )}

      {/* SPEC §31 Agent State */}
      <details className="cit-agentstate">
        <summary>SPEC §31 Agent State record ({v.agent_states.length} checkpoints)</summary>
        <div className="cit-table-wrap">
          <table className="cit-table">
            <thead>
              <tr>
                <th>t (months)</th>
                <th>location</th>
                <th>income</th>
                <th>commute (min)</th>
                <th>transport $/mo</th>
                <th>support</th>
              </tr>
            </thead>
            <tbody>
              {v.agent_states.map((a) => (
                <tr key={a.t}>
                  <td>{formatNumber(a.t)}</td>
                  <td>{a.location}</td>
                  <td>${formatNumber(a.income)}</td>
                  <td>{formatNumber(a.commute_minutes)}</td>
                  <td>${formatNumber(a.monthly_transport_cost)}</td>
                  <td>{a.policy_support >= 0 ? "+" : ""}{a.policy_support.toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>

      {v.not_modelled.length > 0 && (
        <details className="cit-notmodelled">
          <summary>What this view does not model ({v.not_modelled.length})</summary>
          <ul>
            {v.not_modelled.map((n, i) => (
              <li key={i}>{n}</li>
            ))}
          </ul>
        </details>
      )}

      <p className="hint cit-note">{v.provenance}</p>
    </div>
  );
}

function Fact({ k, val }: { k: string; val: string }) {
  return (
    <div className="cit-fact">
      <span className="cit-fact-k">{k}</span>
      <span className="cit-fact-v">{val}</span>
    </div>
  );
}

function DeltaTile({
  label,
  unit,
  before,
  after,
  lowerIsBetter,
}: {
  label: string;
  unit: string;
  before: number;
  after: number;
  lowerIsBetter: boolean;
}) {
  const delta = after - before;
  const eps = Math.max(0.01, Math.abs(before) * 0.005);
  let tone = "neutral";
  if (Math.abs(delta) > eps) {
    const improved = lowerIsBetter ? delta < 0 : delta > 0;
    tone = improved ? "good" : "bad";
  }
  const pct = before !== 0 ? (delta / Math.abs(before)) * 100 : null;
  return (
    <div className="cit-tile">
      <span className="cit-tile-label">{label}</span>
      <span className="cit-tile-vals">
        {formatNumber(before)} → <strong>{formatNumber(after)}</strong>{" "}
        <span className="cit-tile-unit">{unit}</span>
      </span>
      <span className={`cit-tile-delta ${tone}`}>
        {Math.abs(delta) <= eps
          ? "≈ 0 (no change)"
          : `${signed(delta)} ${unit}${
              pct != null ? ` · ${signed(Math.round(pct))}%` : ""
            }`}
      </span>
      <span className="tag simulated">Simulated</span>
    </div>
  );
}

function SupportTile({ snap }: { snap: CitizenSnapshot }) {
  const tone = stanceTone(snap.stance);
  // Map support in [-1, 1] → [0, 100]% for the gauge.
  const pos = ((snap.policy_support + 1) / 2) * 100;
  return (
    <div className="cit-tile">
      <span className="cit-tile-label">Policy support (SPEC §31)</span>
      <span className="cit-tile-vals">
        <strong className={tone}>
          {snap.policy_support >= 0 ? "+" : ""}
          {snap.policy_support.toFixed(2)}
        </strong>{" "}
        <span className={`cit-stance ${tone}`}>{snap.stance}</span>
      </span>
      <div className="cit-gauge" title="latent support on a −1…+1 axis">
        <div className="cit-gauge-mid" />
        <div className={`cit-gauge-fill ${tone}`} style={{ left: `${Math.min(pos, 50)}%`, width: `${Math.abs(pos - 50)}%` }} />
      </div>
      <span className="tag simulated">Simulated</span>
    </div>
  );
}

function TrajectoryTable({
  before,
  trajectory,
}: {
  before: CitizenSnapshot;
  trajectory: CitizenSnapshot[];
}) {
  const rows: Array<{ snap: CitizenSnapshot; isBefore: boolean }> = [
    { snap: before, isBefore: true },
    ...trajectory.map((s) => ({ snap: s, isBefore: false })),
  ];
  return (
    <div className="cit-table-wrap">
      <table className="cit-table cit-traj">
        <thead>
          <tr>
            <th>Checkpoint</th>
            <th>Mode</th>
            <th>Commute (min, band)</th>
            <th>Transport ($/mo, band)</th>
            <th>Charge $/mo</th>
            <th>Support</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(({ snap, isBefore }, i) => (
            <tr key={i} className={isBefore ? "cit-row-before" : ""}>
              <td>
                {snap.label}
                {isBefore && <span className="tag muted cit-inline-tag">World A</span>}
              </td>
              <td>{snap.mode.replace("_", " ")}</td>
              <td>
                {formatNumber(snap.commute_minutes_one_way)}
                <span className="cit-band">
                  {" "}
                  [{formatNumber(snap.commute_minutes_low)}–
                  {formatNumber(snap.commute_minutes_high)}]
                </span>
              </td>
              <td>
                ${formatNumber(snap.monthly_transport_cost)}
                <span className="cit-band">
                  {" "}
                  [${formatNumber(snap.monthly_transport_cost_low)}–$
                  {formatNumber(snap.monthly_transport_cost_high)}]
                </span>
              </td>
              <td>
                {snap.charge_paid_monthly > 0
                  ? `$${formatNumber(snap.charge_paid_monthly)}`
                  : "—"}
              </td>
              <td className={stanceTone(snap.stance)}>
                {snap.policy_support >= 0 ? "+" : ""}
                {snap.policy_support.toFixed(2)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
