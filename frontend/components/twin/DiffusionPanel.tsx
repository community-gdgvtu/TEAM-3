"use client";

/**
 * Opinion-diffusion view (SPEC §14): a deterministic Friedkin–Johnsen run over an
 * abstract social graph from `POST /diffusion`. Renders each actor's opinion
 * trajectory over the information rounds, the issue salience + polarisation
 * curves, and the coalitions that form by the final round.
 *
 * Charts follow the dataviz polarity conventions: opinion is a bipolar scale in
 * [-1,+1], so trajectories are coloured on a diverging support(green) ↔ oppose(red)
 * ramp by their final stance, with a solid zero midline and never colour alone
 * (labels + a legend carry the meaning too). Information shocks are marked on the
 * round axis.
 *
 * Honesty (SPEC §14/§34): rounds are information-diffusion steps, NOT the physical
 * Time-Machine horizon — the panel says so. Every number is Simulated (citizen
 * round-0 opinions seeded from the cohort model, actor priors documented
 * constants); no LLM is on the numeric path. Backend down → honest waiting state.
 */

import { useEffect, useMemo, useState } from "react";

import { runDiffusion } from "../../lib/api";
import type {
  Coalition,
  DiffusionNode,
  DiffusionResult,
  OpinionTrajectory,
} from "../../lib/api";
import { useTwin } from "./TwinStore";

type Status = "idle" | "loading" | "ready" | "error";

// Diverging polarity ramp for a final opinion in [-1,1] (dataviz): green support
// pole, red oppose pole, muted slate for a contested near-zero stance.
function opinionColor(v: number): string {
  if (v > 0.15) return "#3ddc97";
  if (v < -0.15) return "#ff6b6b";
  return "#8a93a8";
}

function stanceLabel(v: number): string {
  if (v > 0.15) return "support";
  if (v < -0.15) return "oppose";
  return "contested";
}

export default function DiffusionPanel() {
  const { policy } = useTwin();
  const [status, setStatus] = useState<Status>("idle");
  const [result, setResult] = useState<DiffusionResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setResult(null);
    setStatus("idle");
    setError(null);
  }, [policy]);

  async function diffuse() {
    if (!policy) return;
    setStatus("loading");
    setError(null);
    try {
      const r = await runDiffusion(policy);
      setResult(r);
      setStatus("ready");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Diffusion model failed");
      setStatus("error");
    }
  }

  const nodeById = useMemo(() => {
    const m = new Map<string, DiffusionNode>();
    if (result) for (const n of result.nodes) m.set(n.id, n);
    return m;
  }, [result]);

  return (
    <section className="card diffusion">
      <div className="dashboard-head">
        <h2>Opinion diffusion</h2>
        <span className="dashboard-sub">
          Friedkin–Johnsen over a social graph · rounds are information steps, not time
        </span>
      </div>

      {!policy ? (
        <div className="waiting">
          <span className="tag muted">No policy yet</span>
          <p>Compile a policy above to watch opinion spread through the social graph.</p>
        </div>
      ) : (
        <>
          <div className="policy-actions" style={{ marginTop: 0 }}>
            <button
              type="button"
              className="btn primary"
              onClick={diffuse}
              disabled={status === "loading"}
            >
              {status === "loading"
                ? "Diffusing…"
                : result
                  ? "Re-run diffusion"
                  : "Run opinion diffusion"}
            </button>
            {result && <span className="tag simulated">Simulated</span>}
          </div>

          {status === "error" && (
            <p className="hint error-text">Couldn&rsquo;t run diffusion: {error}</p>
          )}

          {result && status === "ready" && (
            <div className="diff-body">
              <div className="diff-headline">
                <NetSwing
                  from={result.initial_net_support}
                  to={result.final_net_support}
                />
                <span className="diff-narrative">
                  Dominant narrative:{" "}
                  <strong>{titleCase(result.dominant_narrative)}</strong>
                </span>
              </div>

              <TrajectoryChart
                trajectories={result.trajectories}
                nodeById={nodeById}
                rounds={result.rounds}
                shocks={result.shocks_applied}
              />

              <div className="diff-legend">
                <span className="legend-item">
                  <span className="swatch" style={{ background: "#3ddc97" }} aria-hidden />
                  ends supporting
                </span>
                <span className="legend-item">
                  <span className="swatch" style={{ background: "#ff6b6b" }} aria-hidden />
                  ends opposing
                </span>
                <span className="legend-item">
                  <span className="swatch" style={{ background: "#8a93a8" }} aria-hidden />
                  contested
                </span>
              </div>

              <div className="diff-signals">
                <MiniLine
                  title="Issue salience"
                  series={result.salience}
                  color="#4f8cff"
                  hint="engagement / attention per round"
                />
                <MiniLine
                  title="Polarisation"
                  series={result.polarisation}
                  color="#e0b45f"
                  hint="opinion spread per round"
                />
              </div>

              {result.coalitions.length > 0 && (
                <div className="diff-coalitions">
                  <h3 className="diff-sub">Coalitions by the final round</h3>
                  {[...result.coalitions]
                    .sort((a, b) => b.citizen_share - a.citizen_share)
                    .map((c, i) => (
                      <CoalitionRow key={`${c.stance}-${i}`} c={c} nodeById={nodeById} />
                    ))}
                </div>
              )}

              {result.shocks_applied.length > 0 && (
                <p className="hint diff-shocks">
                  Information shocks applied:{" "}
                  {result.shocks_applied
                    .map((s) => `${s.label || "shock"} @ round ${s.round}`)
                    .join(" · ")}
                </p>
              )}

              <p className="hint diff-note">{result.note}</p>
            </div>
          )}
        </>
      )}
    </section>
  );
}

function NetSwing({ from, to }: { from: number; to: number }) {
  const f = Math.round(from * 100);
  const t = Math.round(to * 100);
  const cls = to > 0.02 ? "pos" : to < -0.02 ? "neg" : "flat";
  return (
    <span className="diff-swing">
      <span className="diff-swing-label">Citizen net support</span>
      <span className="diff-swing-nums">
        <span className="net-chip flat small">
          {f > 0 ? "+" : ""}
          {f}
        </span>
        <span aria-hidden>→</span>
        <span className={`net-chip ${cls}`}>
          {t > 0 ? "+" : ""}
          {t}
        </span>
      </span>
    </span>
  );
}

/** Multi-line opinion trajectory chart, [-1,1] with a zero midline + shock marks. */
function TrajectoryChart({
  trajectories,
  nodeById,
  rounds,
  shocks,
}: {
  trajectories: OpinionTrajectory[];
  nodeById: Map<string, DiffusionNode>;
  rounds: number;
  shocks: DiffusionResult["shocks_applied"];
}) {
  const width = 560;
  const height = 200;
  const pad = 8;
  const maxRound = Math.max(1, rounds);

  const x = (r: number) => pad + (r / maxRound) * (width - 2 * pad);
  // Opinion domain fixed to the full bipolar scale so runs are comparable.
  const y = (v: number) => height / 2 - v * (height / 2 - pad);

  return (
    <div className="diff-chart-wrap">
      <svg
        className="diff-chart"
        viewBox={`0 0 ${width} ${height}`}
        role="img"
        aria-label="Opinion trajectories over diffusion rounds"
        preserveAspectRatio="none"
      >
        {/* +1 / 0 / −1 gridlines; zero is the solid neutral axis. */}
        <line x1={pad} y1={y(1)} x2={width - pad} y2={y(1)} stroke="#263149" strokeWidth={1} strokeDasharray="3 4" />
        <line x1={pad} y1={y(0)} x2={width - pad} y2={y(0)} stroke="#3a4869" strokeWidth={1.25} />
        <line x1={pad} y1={y(-1)} x2={width - pad} y2={y(-1)} stroke="#263149" strokeWidth={1} strokeDasharray="3 4" />

        {/* Shock markers on the round axis. */}
        {shocks.map((s, i) => (
          <line
            key={`shock-${i}`}
            x1={x(s.round)}
            y1={pad}
            x2={x(s.round)}
            y2={height - pad}
            stroke="#e0b45f"
            strokeWidth={1}
            strokeOpacity={0.5}
            strokeDasharray="2 3"
          />
        ))}

        {trajectories.map((tr) => {
          const node = nodeById.get(tr.node_id);
          const final = tr.opinions[tr.opinions.length - 1] ?? 0;
          const color = opinionColor(final);
          // Citizen cohorts (with population) drawn heavier than institutional actors.
          const isCitizen = (node?.size ?? 0) > 0;
          const path = tr.opinions
            .map((v, r) => `${r === 0 ? "M" : "L"}${x(r).toFixed(1)},${y(v).toFixed(1)}`)
            .join(" ");
          return (
            <path
              key={tr.node_id}
              d={path}
              fill="none"
              stroke={color}
              strokeWidth={isCitizen ? 2 : 1.1}
              strokeOpacity={isCitizen ? 0.9 : 0.5}
              strokeLinejoin="round"
              strokeLinecap="round"
            >
              <title>
                {node?.label ?? tr.node_id}: {stanceLabel(final)} (
                {final > 0 ? "+" : ""}
                {final.toFixed(2)})
              </title>
            </path>
          );
        })}
      </svg>
      <div className="diff-axis">
        <span>+1 support</span>
        <span>round 0 → {maxRound}</span>
        <span>−1 oppose</span>
      </div>
    </div>
  );
}

/** Compact single line for a 0–1 signal over rounds (salience / polarisation). */
function MiniLine({
  title,
  series,
  color,
  hint,
}: {
  title: string;
  series: number[];
  color: string;
  hint: string;
}) {
  const width = 240;
  const height = 52;
  const pad = 4;
  const n = series.length;
  if (n === 0) return null;
  const x = (i: number) =>
    n === 1 ? width / 2 : pad + (i / (n - 1)) * (width - 2 * pad);
  const y = (v: number) => height - pad - v * (height - 2 * pad); // 0..1 domain
  const path = series
    .map((v, i) => `${i === 0 ? "M" : "L"}${x(i).toFixed(1)},${y(v).toFixed(1)}`)
    .join(" ");
  const last = series[n - 1];
  return (
    <div className="diff-mini">
      <div className="diff-mini-head">
        <span className="diff-mini-title">{title}</span>
        <span className="diff-mini-val" style={{ color }}>
          {Math.round(last * 100)}%
        </span>
      </div>
      <svg
        className="diff-mini-svg"
        viewBox={`0 0 ${width} ${height}`}
        role="img"
        aria-label={`${title} over rounds`}
        preserveAspectRatio="none"
      >
        <path
          d={path}
          fill="none"
          stroke={color}
          strokeWidth={1.75}
          strokeLinejoin="round"
          strokeLinecap="round"
        />
      </svg>
      <span className="diff-mini-hint">{hint}</span>
    </div>
  );
}

function CoalitionRow({
  c,
  nodeById,
}: {
  c: Coalition;
  nodeById: Map<string, DiffusionNode>;
}) {
  const cls = c.stance === "support" ? "pos" : c.stance === "oppose" ? "neg" : "flat";
  const pct = Math.round(c.citizen_share * 100);
  const names = c.members
    .map((m) => nodeById.get(m)?.label ?? m)
    .slice(0, 5)
    .join(", ");
  const more = c.members.length > 5 ? ` +${c.members.length - 5} more` : "";
  return (
    <div className="diff-coalition">
      <div className="diff-coalition-head">
        <span className={`net-chip ${cls}`}>{c.stance}</span>
        <span className="diff-coalition-share">{pct}% of citizens</span>
        <span className="diff-coalition-mean">
          mean {c.mean_opinion > 0 ? "+" : ""}
          {c.mean_opinion.toFixed(2)}
        </span>
      </div>
      <div className="diff-coalition-bar" aria-hidden>
        <span
          className={`diff-coalition-fill ${cls}`}
          style={{ width: `${Math.max(2, pct)}%` }}
        />
      </div>
      <p className="diff-coalition-members">
        {names}
        {more}
      </p>
    </div>
  );
}

function titleCase(s: string): string {
  return s
    .split(/[-_\s]/)
    .map((w) => (w ? w[0].toUpperCase() + w.slice(1) : w))
    .join(" ");
}
