"use client";

/**
 * System Dynamics / recursive-feedback view (SPEC §7.6/§19): the coupled
 * stocks-and-flows loop SPEC §19 calls "central to the concept" — charge →
 * mode shift → revenue → transit capacity, and negative support → endogenous
 * amendment → weaker charge → less revenue → slower capacity → renewed crowding.
 *
 * The honesty story (SPEC §19/§34): the *magnitudes* the loop pushes toward
 * (demand pull, revenue, support) are Simulated by the deterministic agent-based
 * model; the *temporal coefficients* that couple them over months are documented
 * Estimated assumptions. The integrated trajectory is a deterministic simulation
 * → Simulated, LLM-free. The whole point is the closed-loop (political response
 * ON) vs open-loop (OFF) contrast: recursive feedback changes the outcome, and
 * both runs use the identical model with only the amendment rule toggled. When
 * the backend is down we show an honest waiting/error state, never a fake curve.
 */

import { useEffect, useState } from "react";

import { runDynamics } from "../../lib/api";
import type {
  FeedbackContrast,
  FeedbackEvent,
  StockPoint,
  SystemDynamicsResult,
} from "../../lib/api";
import { formatNumber } from "../../lib/format";
import { useTwin } from "./TwinStore";

type Status = "idle" | "loading" | "ready" | "error";

/** Signed compact number, e.g. +1.2M / −340.0k / 0. */
function signed(v: number): string {
  if (v === 0) return "0";
  const sign = v > 0 ? "+" : "−";
  return `${sign}${formatNumber(Math.abs(v))}`;
}

const EVENT_GLYPH: Record<string, string> = {
  amendment: "✎",
  capacity_exceeded: "▲",
  crowding_relieved: "▽",
  support_recovered: "☑",
};

const EVENT_CLASS: Record<string, string> = {
  amendment: "warn",
  capacity_exceeded: "warn",
  crowding_relieved: "good",
  support_recovered: "good",
};

export default function DynamicsPanel() {
  const { policy } = useTwin();
  const [status, setStatus] = useState<Status>("idle");
  const [result, setResult] = useState<SystemDynamicsResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [politicalResponse, setPoliticalResponse] = useState(true);

  // A fresh/edited policy invalidates any prior run.
  useEffect(() => {
    setResult(null);
    setStatus("idle");
    setError(null);
  }, [policy]);

  async function run() {
    if (!policy) return;
    setStatus("loading");
    setError(null);
    try {
      const r = await runDynamics(policy, politicalResponse);
      setResult(r);
      setStatus("ready");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Dynamics model failed");
      setStatus("error");
    }
  }

  return (
    <section className="card dynamics">
      <div className="dashboard-head">
        <h2>Recursive feedback loop</h2>
        <span className="dashboard-sub">
          System dynamics · closed-loop vs open-loop · deterministic (SPEC §19)
        </span>
      </div>

      {!policy ? (
        <div className="waiting">
          <span className="tag muted">No policy yet</span>
          <p>
            Compile a policy above to integrate the SPEC §19 stocks-and-flows loop:
            the charge drives mode shift and revenue, revenue funds transit
            capacity, and eroding support can force an endogenous amendment that
            cuts the charge — stalling the capacity programme and bringing crowding
            back. Structural magnitudes are <span className="tag simulated">Simulated</span>
            {" "}by the agent-based model; the couplings over time are documented
            assumptions.
          </p>
        </div>
      ) : (
        <>
          <div className="policy-actions dyn-actions" style={{ marginTop: 0 }}>
            <button
              type="button"
              className="btn primary"
              onClick={run}
              disabled={status === "loading"}
            >
              {status === "loading"
                ? "Integrating loop…"
                : result
                  ? "Re-run loop"
                  : "Run feedback loop"}
            </button>
            <label className="dyn-toggle" title="SPEC §19 endogenous political-response arm">
              <input
                type="checkbox"
                checked={politicalResponse}
                onChange={(e) => setPoliticalResponse(e.target.checked)}
                disabled={status === "loading"}
              />
              <span>
                Political response{" "}
                <span className="dyn-toggle-note">
                  (sustained negative support forces an amendment)
                </span>
              </span>
            </label>
            {result && (
              <span className={`tag ${result.provenance.toLowerCase()}`}>
                {result.provenance}
              </span>
            )}
          </div>

          {status === "error" && (
            <p className="hint error-text">Couldn&rsquo;t run the loop: {error}</p>
          )}

          {status === "idle" && !result && (
            <p className="hint">
              Integrates a monthly stock-flow simulation over the 10-year horizon.
              Toggle the political-response arm to see how endogenous amendments
              change the end state, then click to run.
            </p>
          )}

          {result && status !== "loading" && <DynamicsBody r={result} />}
        </>
      )}
    </section>
  );
}

function DynamicsBody({ r }: { r: SystemDynamicsResult }) {
  const final = r.final_state;
  return (
    <div className="dyn-body">
      {/* The SPEC §19 cascade, instantiated for this policy */}
      {r.loop_description.length > 0 && (
        <ol className="dyn-loop">
          {r.loop_description.map((step, i) => (
            <li key={i}>{step}</li>
          ))}
        </ol>
      )}

      {/* Final-state summary */}
      <div className="dyn-final">
        <FinalStat
          label="Charge in force"
          value={formatNumber(final.charge)}
          sub={`at ${formatNumber(final.t_years)}y`}
        />
        <FinalStat
          label="Crowding (demand/capacity)"
          value={`${final.crowding.toFixed(2)}×`}
          sub={final.crowding > 1 ? "over capacity" : "within capacity"}
          tone={final.crowding > 1 ? "warn" : "good"}
        />
        <FinalStat
          label="Net support"
          value={final.support.toFixed(2)}
          sub="[-1 … 1]"
          tone={final.support >= 0 ? "good" : "warn"}
        />
        <FinalStat
          label="Amendments triggered"
          value={String(r.amendments_triggered)}
          sub={r.political_response_enabled ? "loop closed" : "loop open"}
          tone={r.amendments_triggered > 0 ? "warn" : "mid"}
        />
      </div>

      {/* Coupled trajectories */}
      <h3 className="dyn-sec-title">
        Coupled stock trajectories{" "}
        <span className="dyn-sec-note">
          monthly integration over 10y · widening band = confidence (SPEC §9)
        </span>
      </h3>
      <div className="dyn-charts">
        <StockChart
          title="Transit demand vs capacity"
          points={r.trajectory}
          series={[
            { key: "transit_demand", label: "Demand", color: "#f2994a" },
            { key: "transit_capacity", label: "Capacity", color: "#4f8cff" },
          ]}
          unit="trips/day"
        />
        <StockChart
          title="Crowding ratio"
          points={r.trajectory}
          series={[{ key: "crowding", label: "Demand ÷ capacity", color: "#eb5757" }]}
          baseline={1}
          baselineLabel="over-capacity"
        />
        <StockChart
          title="Effective charge"
          points={r.trajectory}
          series={[{ key: "charge", label: "Charge in force", color: "#9b6dff" }]}
          unit="currency"
        />
        <StockChart
          title="Net public support"
          points={r.trajectory}
          series={[{ key: "support", label: "Support", color: "#27ae60" }]}
          baseline={0}
          baselineLabel="neutral"
        />
      </div>

      {/* Closed vs open loop contrast — the point of SPEC §19 */}
      {r.contrast.length > 0 && (
        <>
          <h3 className="dyn-sec-title">
            Closed-loop vs open-loop end state{" "}
            <span className="dyn-sec-note">
              same model, only the amendment rule toggled — this is why recursion matters
            </span>
          </h3>
          <div className="dyn-contrast">
            {r.contrast.map((c) => (
              <ContrastRow key={c.metric} c={c} />
            ))}
          </div>
        </>
      )}

      {/* Second-order feedback events */}
      {r.feedback_events.length > 0 && (
        <>
          <h3 className="dyn-sec-title">
            Feedback events{" "}
            <span className="dyn-sec-note">second-order effects the loop produced</span>
          </h3>
          <div className="dyn-events">
            {r.feedback_events.map((e, i) => (
              <EventRow key={i} e={e} />
            ))}
          </div>
        </>
      )}

      {r.not_modelled.length > 0 && (
        <div className="dyn-notmodelled">
          <span className="dyn-nm-title">Deliberately not modelled</span>
          <ul>
            {r.not_modelled.map((n, i) => (
              <li key={i}>{n}</li>
            ))}
          </ul>
        </div>
      )}

      <ProvenanceBlock
        title="Structural anchors"
        subtitle="from the agent-based model"
        tag="Simulated"
        data={r.anchors}
      />
      <ProvenanceBlock
        title="Dynamics assumptions"
        subtitle="temporal coefficients — auditable inputs"
        tag="Estimated"
        data={r.params}
      />

      <p className="hint dyn-note">{r.note}</p>
    </div>
  );
}

function FinalStat({
  label,
  value,
  sub,
  tone = "mid",
}: {
  label: string;
  value: string;
  sub?: string;
  tone?: "good" | "warn" | "mid";
}) {
  return (
    <div className="dyn-stat">
      <span className="dyn-stat-label">{label}</span>
      <span className={`dyn-stat-value ${tone}`}>{value}</span>
      {sub && <span className="dyn-stat-sub">{sub}</span>}
    </div>
  );
}

interface Series {
  key: keyof StockPoint;
  label: string;
  color: string;
}

/**
 * Pure-SVG multi-series stock chart with a widening confidence band around the
 * first series (SPEC §9). No chart lib — keeps the panel lightweight and the
 * band unmistakable. The band half-width scales with (1 − confidence) so it
 * widens exactly as the model's confidence falls over the horizon.
 */
function StockChart({
  title,
  points,
  series,
  unit,
  baseline,
  baselineLabel,
}: {
  title: string;
  points: StockPoint[];
  series: Series[];
  unit?: string;
  baseline?: number;
  baselineLabel?: string;
}) {
  const width = 300;
  const height = 120;
  const pad = 8;
  const n = points.length;
  if (n === 0) return null;

  // y-domain across every plotted series + the band + any baseline line.
  let lo = Infinity;
  let hi = -Infinity;
  const bandFor = (p: StockPoint, v: number) => {
    const half = Math.abs(v) * (1 - p.confidence) * 0.5;
    return { low: v - half, high: v + half };
  };
  for (const p of points) {
    for (const s of series) {
      const v = Number(p[s.key]);
      lo = Math.min(lo, v);
      hi = Math.max(hi, v);
    }
    const first = Number(p[series[0].key]);
    const b = bandFor(p, first);
    lo = Math.min(lo, b.low);
    hi = Math.max(hi, b.high);
  }
  if (baseline != null) {
    lo = Math.min(lo, baseline);
    hi = Math.max(hi, baseline);
  }
  if (lo === hi) {
    hi = lo + 1;
    lo -= 1;
  }
  const span = hi - lo;
  // Small headroom so lines don't touch the frame.
  lo -= span * 0.06;
  hi += span * 0.06;

  const x = (i: number) =>
    n === 1 ? width / 2 : pad + (i / (n - 1)) * (width - 2 * pad);
  const y = (v: number) =>
    height - pad - ((v - lo) / (hi - lo)) * (height - 2 * pad);

  const first = series[0];
  const bandTop = points.map((p, i) => `${x(i)},${y(bandFor(p, Number(p[first.key])).high)}`);
  const bandBottom = points
    .slice()
    .reverse()
    .map((p, ri) => {
      const i = n - 1 - ri;
      return `${x(i)},${y(bandFor(p, Number(p[first.key])).low)}`;
    });
  const bandPath = `${bandTop.join(" ")} ${bandBottom.join(" ")}`;

  return (
    <figure className="dyn-chart">
      <figcaption className="dyn-chart-title">
        {title}
        {unit && <span className="dyn-chart-unit"> · {unit}</span>}
      </figcaption>
      <svg
        className="dyn-svg"
        width="100%"
        viewBox={`0 0 ${width} ${height}`}
        preserveAspectRatio="none"
        role="img"
        aria-label={`${title} trajectory over 10 years with uncertainty band`}
      >
        <polygon points={bandPath} fill={first.color} fillOpacity={0.14} stroke="none" />
        {baseline != null && (
          <line
            x1={pad}
            y1={y(baseline)}
            x2={width - pad}
            y2={y(baseline)}
            stroke="#8892a6"
            strokeDasharray="3 3"
            strokeWidth={1}
          />
        )}
        {series.map((s) => {
          const linePath = points.map((p, i) => `${x(i)},${y(Number(p[s.key]))}`).join(" ");
          return (
            <polyline
              key={String(s.key)}
              points={linePath}
              fill="none"
              stroke={s.color}
              strokeWidth={1.9}
              strokeLinejoin="round"
              strokeLinecap="round"
            />
          );
        })}
      </svg>
      <div className="dyn-legend">
        {series.map((s) => (
          <span key={String(s.key)} className="dyn-leg-item">
            <span className="dyn-leg-swatch" style={{ background: s.color }} />
            {s.label}
          </span>
        ))}
        {baselineLabel && (
          <span className="dyn-leg-item dyn-leg-base">
            <span className="dyn-leg-swatch dyn-leg-swatch-dash" />
            {baselineLabel}
          </span>
        )}
      </div>
    </figure>
  );
}

function ContrastRow({ c }: { c: FeedbackContrast }) {
  const tone = c.delta > 0 ? "good" : c.delta < 0 ? "warn" : "mid";
  return (
    <div className="dyn-contrast-row">
      <span className="dyn-contrast-metric">{c.metric.replace(/_/g, " ")}</span>
      <div className="dyn-contrast-vals">
        <span className="dyn-contrast-cell">
          <span className="dyn-contrast-tag">closed</span>
          <strong>{formatNumber(c.closed_loop)}</strong>
        </span>
        <span className="dyn-contrast-cell">
          <span className="dyn-contrast-tag">open</span>
          <strong>{formatNumber(c.open_loop)}</strong>
        </span>
        <span className={`dyn-contrast-delta ${tone}`}>{signed(c.delta)}</span>
      </div>
      <p className="dyn-contrast-interp">{c.interpretation}</p>
    </div>
  );
}

function EventRow({ e }: { e: FeedbackEvent }) {
  const cls = EVENT_CLASS[e.type] ?? "mid";
  const years = (e.t_months / 12).toFixed(1);
  return (
    <div className="dyn-event">
      <div className="dyn-event-head">
        <span className={`dyn-event-glyph ${cls}`} title={e.type}>
          {EVENT_GLYPH[e.type] ?? "◆"}
        </span>
        <span className="dyn-event-label">{e.label}</span>
        <span className="dyn-event-time">
          month {formatNumber(e.t_months)} · {years}y
        </span>
      </div>
      {e.cause_chain.length > 0 && (
        <ol className="dyn-cause">
          {e.cause_chain.map((step, i) => (
            <li key={i}>{step}</li>
          ))}
        </ol>
      )}
    </div>
  );
}

function ProvenanceBlock({
  title,
  subtitle,
  tag,
  data,
}: {
  title: string;
  subtitle: string;
  tag: string;
  data: Record<string, unknown>;
}) {
  const entries = Object.entries(data ?? {});
  if (entries.length === 0) return null;
  return (
    <details className="dyn-provenance">
      <summary>
        {title}{" "}
        <span className={`tag ${tag.toLowerCase()}`}>{tag}</span>
        <span className="dyn-prov-sub"> · {subtitle}</span>
        <span className="dyn-prov-count"> ({entries.length})</span>
      </summary>
      <dl>
        {entries.map(([k, v]) => (
          <div key={k} className="dyn-prov-row">
            <dt>{k.replace(/_/g, " ")}</dt>
            <dd>{typeof v === "object" ? JSON.stringify(v) : String(v)}</dd>
          </div>
        ))}
      </dl>
    </details>
  );
}
