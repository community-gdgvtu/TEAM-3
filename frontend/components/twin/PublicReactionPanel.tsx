"use client";

/**
 * Public reaction view (SPEC §13/§27): the cohort opinion distribution from
 * `POST /public`, rendered as diverging Likert bars — overall, then broken out by
 * a switchable dimension (income band / geography / travel mode).
 *
 * Charts follow the dataviz conventions: opinion is a *polarity* scale, so it uses
 * a diverging ramp (green support pole ↔ red oppose pole, gray neutral, muted
 * "uncertain"), poles dark and centre light, 2px surface gaps between segments,
 * direct % labels + a shared legend as secondary encoding (never colour alone),
 * and per-segment hover tooltips.
 *
 * Provenance (SPEC §34): the whole pipeline is a deterministic structural model —
 * every fraction is Simulated, not a poll. No LLM produced any number.
 */

import { useEffect, useMemo, useState } from "react";

import { runPublicOpinion } from "../../lib/api";
import type {
  CohortOpinion,
  OpinionDistribution,
  PublicOpinion,
} from "../../lib/api";
import { useTwin } from "./TwinStore";

type BucketKey =
  | "strong_support"
  | "support"
  | "neutral"
  | "oppose"
  | "strong_oppose"
  | "uncertain";

interface BucketMeta {
  key: BucketKey;
  label: string;
  color: string;
}

// Diverging polarity ramp: support pole (green) ↔ oppose pole (red), poles dark /
// mid-arms light, neutral gray midpoint, uncertain muted slate (secondary channel).
const BUCKETS: BucketMeta[] = [
  { key: "strong_support", label: "Strong support", color: "#0f8a3c" },
  { key: "support", label: "Support", color: "#56c07a" },
  { key: "neutral", label: "Neutral", color: "#8a8a82" },
  { key: "oppose", label: "Oppose", color: "#e8895f" },
  { key: "strong_oppose", label: "Strong oppose", color: "#cf3b3b" },
  { key: "uncertain", label: "Uncertain", color: "#5a6172" },
];

type Dimension = "income_band" | "geography" | "travel_mode";

const DIMENSIONS: Array<{ key: Dimension; label: string }> = [
  { key: "income_band", label: "Income band" },
  { key: "geography", label: "Geography" },
  { key: "travel_mode", label: "Travel mode" },
];

// Present low→high so income reads in a natural order; unknown bands sort last.
const INCOME_ORDER = ["low", "lower-middle", "middle", "upper-middle", "high"];

type Status = "idle" | "loading" | "ready" | "error";

export default function PublicReactionPanel() {
  const { policy } = useTwin();
  const [status, setStatus] = useState<Status>("idle");
  const [opinion, setOpinion] = useState<PublicOpinion | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [dimension, setDimension] = useState<Dimension>("income_band");

  useEffect(() => {
    setOpinion(null);
    setStatus("idle");
    setError(null);
  }, [policy]);

  async function gauge() {
    if (!policy) return;
    setStatus("loading");
    setError(null);
    try {
      const o = await runPublicOpinion(policy);
      setOpinion(o);
      setStatus("ready");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Public model failed");
      setStatus("error");
    }
  }

  const groups = useMemo(
    () => (opinion ? aggregate(opinion.cohorts, dimension) : []),
    [opinion, dimension],
  );

  return (
    <section className="card public">
      <div className="dashboard-head">
        <h2>Public reaction</h2>
        <span className="dashboard-sub">
          Cohort opinion model · deterministic, every fraction Simulated (not a poll)
        </span>
      </div>

      {!policy ? (
        <div className="waiting">
          <span className="tag muted">No policy yet</span>
          <p>Compile a policy above to model how the public would react.</p>
        </div>
      ) : (
        <>
          <div className="policy-actions" style={{ marginTop: 0 }}>
            <button
              type="button"
              className="btn primary"
              onClick={gauge}
              disabled={status === "loading"}
            >
              {status === "loading"
                ? "Modelling…"
                : opinion
                  ? "Re-gauge reaction"
                  : "Gauge public reaction"}
            </button>
            {opinion && (
              <span className="tag simulated">Simulated</span>
            )}
          </div>

          {status === "error" && (
            <p className="hint error-text">Couldn&rsquo;t model reaction: {error}</p>
          )}

          {opinion && status === "ready" && (
            <div className="public-body">
              <div className="public-overall">
                <div className="public-overall-head">
                  <span className="public-overall-label">
                    Overall · {opinion.population.toLocaleString()} agents
                  </span>
                  <NetChip net={opinion.overall.net_support} />
                </div>
                <LikertBar dist={opinion.overall} />
              </div>

              <Legend />

              <div className="public-dim">
                <span className="ctrl-label">Break down by</span>
                <div className="seg" role="group" aria-label="Break down by">
                  {DIMENSIONS.map((d) => (
                    <button
                      key={d.key}
                      type="button"
                      className={`seg-btn${dimension === d.key ? " active" : ""}`}
                      onClick={() => setDimension(d.key)}
                    >
                      {d.label}
                    </button>
                  ))}
                </div>
              </div>

              <div className="cohort-rows">
                {groups.map((g) => (
                  <div key={g.label} className="cohort-row">
                    <div className="cohort-row-head">
                      <span className="cohort-name">{titleCase(g.label)}</span>
                      <span className="cohort-meta">
                        <span className="cohort-size">
                          {g.size.toLocaleString()}
                        </span>
                        <NetChip net={g.dist.net_support} small />
                      </span>
                    </div>
                    <LikertBar dist={g.dist} />
                  </div>
                ))}
              </div>

              <p className="hint public-note">{opinion.note}</p>
            </div>
          )}
        </>
      )}
    </section>
  );
}

/** Size-weighted aggregation of cohorts into groups along one dimension. */
function aggregate(
  cohorts: CohortOpinion[],
  dim: Dimension,
): Array<{ label: string; size: number; dist: OpinionDistribution }> {
  const acc = new Map<
    string,
    { size: number; sums: Record<BucketKey, number> }
  >();
  for (const c of cohorts) {
    const label = String(c[dim]);
    let g = acc.get(label);
    if (!g) {
      g = {
        size: 0,
        sums: {
          strong_support: 0,
          support: 0,
          neutral: 0,
          oppose: 0,
          strong_oppose: 0,
          uncertain: 0,
        },
      };
      acc.set(label, g);
    }
    g.size += c.size;
    for (const b of BUCKETS) {
      g.sums[b.key] += c.distribution[b.key] * c.size;
    }
  }

  const out = Array.from(acc.entries()).map(([label, g]) => {
    const d = {} as OpinionDistribution;
    for (const b of BUCKETS) {
      (d as Record<BucketKey, number>)[b.key] =
        g.size > 0 ? g.sums[b.key] / g.size : 0;
    }
    d.net_support =
      d.strong_support + d.support - d.oppose - d.strong_oppose;
    return { label, size: g.size, dist: d };
  });

  // Order income bands low→high; otherwise sort by net support (most opposed last).
  out.sort((a, b) => {
    const ia = INCOME_ORDER.indexOf(a.label);
    const ib = INCOME_ORDER.indexOf(b.label);
    if (ia !== -1 || ib !== -1) {
      return (ia === -1 ? 99 : ia) - (ib === -1 ? 99 : ib);
    }
    return b.dist.net_support - a.dist.net_support;
  });
  return out;
}

/** 100% diverging Likert bar: ordered segments, 2px surface gaps, hover + labels. */
function LikertBar({ dist }: { dist: OpinionDistribution }) {
  return (
    <div className="likert" role="img" aria-label="Opinion distribution">
      {BUCKETS.map((b) => {
        const frac = (dist as Record<BucketKey, number>)[b.key];
        const pct = Math.round(frac * 100);
        if (frac <= 0) return null;
        return (
          <span
            key={b.key}
            className="likert-seg"
            style={{ flexGrow: frac, background: b.color }}
            title={`${b.label}: ${pct}%`}
          >
            {/* Direct label only where the segment is wide enough to read. */}
            {frac >= 0.08 && <span className="likert-pct">{pct}%</span>}
          </span>
        );
      })}
    </div>
  );
}

function NetChip({ net, small }: { net: number; small?: boolean }) {
  const pct = Math.round(net * 100);
  const cls = net > 0.02 ? "pos" : net < -0.02 ? "neg" : "flat";
  return (
    <span className={`net-chip ${cls}${small ? " small" : ""}`}>
      net {pct > 0 ? "+" : ""}
      {pct}
    </span>
  );
}

function Legend() {
  return (
    <div className="likert-legend">
      {BUCKETS.map((b) => (
        <span key={b.key} className="legend-item">
          <span className="swatch" style={{ background: b.color }} aria-hidden />
          {b.label}
        </span>
      ))}
    </div>
  );
}

function titleCase(s: string): string {
  return s
    .split(/[-_]/)
    .map((w) => (w ? w[0].toUpperCase() + w.slice(1) : w))
    .join(" ");
}
