"use client";

/**
 * Business View — follow one firm through the Time Machine (SPEC §17 Business View).
 *
 * Every other analysis tab aggregates the economy; this one drills down to a
 * single synthetic firm and shows its before/after operating picture under the
 * policy: its profile, its World-A (no-policy) footfall / labour access /
 * deliveries / costs / revenue proxy, and how each evolves across the
 * Time-Machine checkpoints, the adaptation decisions its exposure implies, and a
 * deterministic "Why?" narrative.
 *
 * A "click a firm" picker (`GET /business/sample`, policy-independent) spans
 * sectors and the central/outer split; five archetype selectors (representative /
 * most-exposed / biggest-footfall-loss / pedestrian-winner / largest) let the
 * judge jump to the firm a question is really about. `POST /business` then
 * returns that firm's staged trajectory.
 *
 * Honesty (SPEC §17/§34): labour accessibility reuses the *same* deterministic
 * mode-choice model as `/simulate` (the commute generalized cost of the firm's
 * own workers); footfall / deliveries / cost / revenue reuse the *same* economic
 * coefficients as `/economy`, staged on the *same* adaptation curve as the
 * aggregate Time Machine — so a firm's numbers can never disagree with the
 * dashboard beside it. No LLM touches the numeric path. The firm is a synthetic
 * micro-agent (SPEC §6), never a real business → Simulated; the revenue figure is
 * an Estimated proxy, meaningful only as a before/after ratio, never an absolute
 * turnover. Footfall / cost / revenue bands widen with the horizon. Idle /
 * loading / error states are shown honestly when the backend is down — a firm is
 * never fabricated.
 */

import { useEffect, useRef, useState } from "react";

import {
  BUSINESS_SELECTORS,
  getBusinessSample,
  runBusiness,
} from "../../lib/api";
import type {
  BusinessSelector,
  BusinessView,
  FirmSample,
  FirmSnapshot,
} from "../../lib/api";
import { formatNumber } from "../../lib/format";
import { useTwin } from "./TwinStore";

type Status = "idle" | "loading" | "ready" | "error";

/** Human labels for the archetype selectors. */
const SELECTOR_LABELS: Record<BusinessSelector, string> = {
  representative: "Representative",
  most_exposed: "Most exposed",
  biggest_footfall_loss: "Biggest footfall loss",
  pedestrian_winner: "Pedestrian winner",
  largest: "Largest",
};

/** Signed value with a fixed style. */
function signed(v: number): string {
  return `${v > 0 ? "+" : ""}${formatNumber(v)}`;
}

export default function BusinessPanel() {
  const { policy } = useTwin();
  const [status, setStatus] = useState<Status>("idle");
  const [view, setView] = useState<BusinessView | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [selector, setSelector] = useState<BusinessSelector>("representative");
  const [firmId, setFirmId] = useState<string | null>(null);

  const [samples, setSamples] = useState<FirmSample[]>([]);
  const [sampleErr, setSampleErr] = useState<string | null>(null);
  const loadedSamples = useRef(false);

  // Populate the firm picker once (policy-independent, SPEC §17).
  useEffect(() => {
    if (loadedSamples.current) return;
    loadedSamples.current = true;
    getBusinessSample(6)
      .then(setSamples)
      .catch((e: unknown) =>
        setSampleErr(e instanceof Error ? e.message : "Sample unavailable"),
      );
  }, []);

  // A fresh/edited policy invalidates any prior firm trajectory.
  useEffect(() => {
    setView(null);
    setStatus("idle");
    setError(null);
  }, [policy]);

  async function run(sel: BusinessSelector, id: string | null) {
    if (!policy) return;
    setSelector(sel);
    setFirmId(id);
    setStatus("loading");
    setError(null);
    try {
      const r = await runBusiness(policy, { select: sel, firmId: id });
      setView(r);
      setStatus("ready");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Business model failed");
      setStatus("error");
    }
  }

  return (
    <section className="card biz">
      <div className="dashboard-head">
        <h2>Business View</h2>
        <span className="dashboard-sub">
          Click a firm — one business through the Time Machine (SPEC §17)
        </span>
      </div>

      {!policy ? (
        <div className="waiting">
          <span className="tag muted">No policy yet</span>
          <p>
            Compile a policy above to follow a single firm&rsquo;s before/after
            footfall, labour access, deliveries, costs and revenue proxy across
            the horizon. Every number reuses the same deterministic models as the
            dashboard beside it — no LLM on the numeric path.
          </p>
        </div>
      ) : (
        <>
          <p className="hint cit-consistency">
            One synthetic firm (SPEC §6) — not a real business. Labour access
            reuses the same deterministic mode-choice model as{" "}
            <strong>/simulate</strong>; footfall, deliveries, cost and revenue
            reuse the same economic coefficients as <strong>/economy</strong>,
            staged on the same adaptation curve as the aggregate Time Machine — so
            this firm can never disagree with the dashboard. Revenue is an
            Estimated proxy (before/after ratio only, never turnover). No LLM
            touches the numeric path (SPEC §34).
          </p>

          <div className="cit-controls">
            <div className="cit-selectors" role="group" aria-label="Pick by archetype">
              <span className="run-label">Pick by archetype</span>
              <div className="cit-chiprow">
                {BUSINESS_SELECTORS.map((s) => (
                  <button
                    key={s}
                    type="button"
                    className={`chip cit-chip${
                      status !== "loading" && firmId === null && selector === s
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
              <div className="cit-samples" role="group" aria-label="Click a firm">
                <span className="run-label">Or click a firm</span>
                <div className="cit-chiprow">
                  {samples.map((f) => (
                    <button
                      key={f.firm_id}
                      type="button"
                      className={`chip cit-chip cit-sample${
                        firmId === f.firm_id ? " active" : ""
                      }`}
                      onClick={() => run(selector, f.firm_id)}
                      disabled={status === "loading"}
                      title={f.label}
                    >
                      <span className="cit-sample-id">{f.firm_id}</span>
                      <span className="cit-sample-label">
                        {f.sector}
                        {f.in_central_district ? " · central" : ""}
                      </span>
                    </button>
                  ))}
                </div>
              </div>
            )}
            {sampleErr && (
              <p className="hint">
                Firm picker unavailable ({sampleErr}) — the archetype selectors
                above still work.
              </p>
            )}
          </div>

          {status === "loading" && (
            <p className="hint">Following this firm through the Time Machine…</p>
          )}
          {status === "error" && <p className="hint error-text">{error}</p>}

          {view && status !== "loading" && <BusinessResult v={view} />}
        </>
      )}
    </section>
  );
}

function BusinessResult({ v }: { v: BusinessView }) {
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
          <span className="cit-profile-id">{p.firm_id}</span>
          <span className="tag simulated">Simulated firm</span>
        </div>
        <div className="cit-profile-grid">
          <Fact k="Sector" val={p.sector} />
          <Fact k="Building kind" val={p.building_kind} />
          <Fact k="Zone" val={p.zone_id} />
          <Fact
            k="District"
            val={p.in_central_district ? "central (priced)" : "outer"}
          />
          <Fact k="Floors" val={`${p.floors}`} />
          <Fact
            k="Floor area"
            val={`${formatNumber(Math.round(p.floor_area_sqm))} m²`}
          />
          <Fact k="Estimated jobs" val={`${formatNumber(p.estimated_jobs)}`} />
        </div>
        <p className="cit-provenance">{p.provenance}</p>
      </div>

      {/* Before → after topline */}
      <div className="cit-beforeafter biz-tiles">
        <DeltaTile
          label="Daily footfall"
          unit="/day"
          before={before.daily_footfall}
          after={end.daily_footfall}
          higherIsBetter
          tag="simulated"
        />
        <DeltaTile
          label="Labour access index"
          unit="(100 = base)"
          before={before.labour_accessibility_index}
          after={end.labour_accessibility_index}
          higherIsBetter
          tag="simulated"
        />
        <DeltaTile
          label="Daily deliveries"
          unit="/day"
          before={before.daily_deliveries}
          after={end.daily_deliveries}
          neutral
          tag="simulated"
        />
        <AbsoluteTile
          label="Added annual cost"
          value={end.annual_cost_added}
          low={end.annual_cost_added_low}
          high={end.annual_cost_added_high}
          prefix="$"
          suffix="/yr"
          badWhenPositive
          tag="estimated"
        />
        <NetRevenueTile snap={end} />
      </div>

      {/* Trajectory through the Time Machine */}
      <h3 className="cit-sub">Through the Time Machine</h3>
      <p className="cit-sub-note">
        World-A (no policy) reference, then this firm&rsquo;s operating picture at
        each checkpoint. Footfall, cost &amp; revenue bands widen with the horizon
        (SPEC §9/§34).
      </p>
      <TrajectoryTable before={before} trajectory={v.trajectory} />

      {/* Adaptation decisions */}
      {v.adaptation_decisions.length > 0 && (
        <>
          <h3 className="cit-sub">Adaptation decisions</h3>
          <p className="cit-sub-note">
            Deterministic firm responses implied by this firm&rsquo;s exposure —
            rules, not an optimised behavioural firm-response simulation
            (SPEC §17).
          </p>
          <ul className="biz-adapt">
            {v.adaptation_decisions.map((d, i) => (
              <li key={i} className="biz-adapt-card">
                {d}
              </li>
            ))}
          </ul>
        </>
      )}

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

/** A before → after tile with signed Δ, %, and good/bad colouring. */
function DeltaTile({
  label,
  unit,
  before,
  after,
  higherIsBetter,
  neutral,
  tag,
}: {
  label: string;
  unit: string;
  before: number;
  after: number;
  higherIsBetter?: boolean;
  neutral?: boolean;
  tag: "simulated" | "estimated";
}) {
  const delta = after - before;
  const eps = Math.max(0.05, Math.abs(before) * 0.005);
  let tone = "neutral";
  if (!neutral && Math.abs(delta) > eps) {
    const improved = higherIsBetter ? delta > 0 : delta < 0;
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
          : `${signed(delta)}${
              pct != null ? ` · ${signed(Math.round(pct))}%` : ""
            }`}
      </span>
      <span className={`tag ${tag}`}>
        {tag === "simulated" ? "Simulated" : "Estimated"}
      </span>
    </div>
  );
}

/** A single absolute value with a band (e.g. added cost, which has no "before"). */
function AbsoluteTile({
  label,
  value,
  low,
  high,
  prefix,
  suffix,
  badWhenPositive,
  tag,
}: {
  label: string;
  value: number;
  low: number;
  high: number;
  prefix?: string;
  suffix?: string;
  badWhenPositive?: boolean;
  tag: "simulated" | "estimated";
}) {
  const tone = badWhenPositive && value > 0.5 ? "bad" : "neutral";
  return (
    <div className="cit-tile">
      <span className="cit-tile-label">{label}</span>
      <span className="cit-tile-vals">
        <strong className={tone}>
          {prefix}
          {formatNumber(value)}
        </strong>{" "}
        <span className="cit-tile-unit">{suffix}</span>
      </span>
      <span className="cit-band">
        band {prefix}
        {formatNumber(low)}–{prefix}
        {formatNumber(high)}
      </span>
      <span className={`tag ${tag}`}>
        {tag === "simulated" ? "Simulated" : "Estimated"}
      </span>
    </div>
  );
}

/** Net revenue proxy % change — the firm's headline economic outcome. */
function NetRevenueTile({ snap }: { snap: FirmSnapshot }) {
  const v = snap.net_revenue_proxy_change_pct;
  const eps = 0.05;
  let tone = "neutral";
  if (Math.abs(v) > eps) tone = v > 0 ? "good" : "bad";
  return (
    <div className="cit-tile">
      <span className="cit-tile-label">Net revenue proxy Δ</span>
      <span className="cit-tile-vals">
        <strong className={tone}>
          {v >= 0 ? "+" : ""}
          {v.toFixed(1)}%
        </strong>
      </span>
      <span className="cit-tile-delta neutral">vs baseline, after added costs</span>
      <span className="tag estimated">Estimated proxy</span>
    </div>
  );
}

function TrajectoryTable({
  before,
  trajectory,
}: {
  before: FirmSnapshot;
  trajectory: FirmSnapshot[];
}) {
  const rows: Array<{ snap: FirmSnapshot; isBefore: boolean }> = [
    { snap: before, isBefore: true },
    ...trajectory.map((s) => ({ snap: s, isBefore: false })),
  ];
  return (
    <div className="cit-table-wrap">
      <table className="cit-table cit-traj">
        <thead>
          <tr>
            <th>Checkpoint</th>
            <th>Footfall/day (band)</th>
            <th>Labour access</th>
            <th>Deliveries/day</th>
            <th>Added cost $/yr</th>
            <th>Net rev. Δ%</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(({ snap, isBefore }, i) => {
            const netTone =
              Math.abs(snap.net_revenue_proxy_change_pct) <= 0.05
                ? "neutral"
                : snap.net_revenue_proxy_change_pct > 0
                  ? "good"
                  : "bad";
            return (
              <tr key={i} className={isBefore ? "cit-row-before" : ""}>
                <td>
                  {snap.label}
                  {isBefore && (
                    <span className="tag muted cit-inline-tag">World A</span>
                  )}
                </td>
                <td>
                  {formatNumber(snap.daily_footfall)}
                  <span className="cit-band">
                    {" "}
                    [{formatNumber(snap.daily_footfall_low)}–
                    {formatNumber(snap.daily_footfall_high)}]
                  </span>
                </td>
                <td>{formatNumber(snap.labour_accessibility_index)}</td>
                <td>{formatNumber(snap.daily_deliveries)}</td>
                <td>
                  {snap.annual_cost_added > 0.5
                    ? `$${formatNumber(snap.annual_cost_added)}`
                    : "—"}
                </td>
                <td className={netTone}>
                  {snap.net_revenue_proxy_change_pct >= 0 ? "+" : ""}
                  {snap.net_revenue_proxy_change_pct.toFixed(1)}%
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
