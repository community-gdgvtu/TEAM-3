"use client";

/**
 * Evidence Drawer (SPEC §26): click any dashboard metric → walk the causal trace
 * down to the underlying evidence — input-data → transform → model → assumptions
 * → result — with the equations/parameters (behavioural levers), the named
 * assumptions, illustrative real-world analogues, citations, and a horizon-aware
 * confidence.
 *
 * Fetches `POST /evidence` for the clicked metric key at the current Time Machine
 * horizon — or, in `example` mode, the keyless `GET /evidence/example` for the
 * canonical §26 peak-transit metric on the §28 demo congestion charge, so a judge
 * landing cold with no compiled policy can still open the drawer and walk the full
 * causal ladder. Provenance (SPEC §34): every number here is copied straight from
 * the deterministic simulation (World A / World B / Δ); analogues and citations
 * are static reference facts. No LLM produced or edited a number on this path —
 * the drawer only re-exposes what the model computed.
 */

import { useEffect, useState } from "react";

import { getEvidenceExample, runEvidence } from "../../lib/api";
import type {
  BehaviouralRule,
  PolicyDSL,
  ProvenanceTrace,
  TraceAssumption,
  TraceStep,
  HistoricalAnalogue,
} from "../../lib/api";
import { formatNumber, formatSignedPct } from "../../lib/format";

export interface EvidenceDrawerProps {
  /** Compiled policy to trace. Omitted in `example` mode. */
  policy?: PolicyDSL;
  /** Metric key to trace, e.g. `traffic.daily_vehicle_km`. Omitted in `example` mode. */
  metricKey?: string;
  horizonMonths?: number;
  /**
   * Open the keyless `GET /evidence/example` trace (canonical §26 metric on the
   * §28 demo policy) instead of `POST /evidence` — reachable with no compiled
   * policy. Mints no numbers of its own; stamped as the demo, not the user's policy.
   */
  example?: boolean;
  onClose: () => void;
}

type Status = "loading" | "ready" | "error";

export default function EvidenceDrawer({
  policy,
  metricKey,
  horizonMonths,
  example = false,
  onClose,
}: EvidenceDrawerProps) {
  const [status, setStatus] = useState<Status>("loading");
  const [trace, setTrace] = useState<ProvenanceTrace | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Refetch whenever the metric or horizon changes. In example mode the keyless
  // GET is used (no policy/metric/horizon inputs); otherwise the POST endpoint.
  useEffect(() => {
    const ctrl = new AbortController();
    setStatus("loading");
    setError(null);
    const pending =
      example || !policy || !metricKey
        ? getEvidenceExample(ctrl.signal)
        : runEvidence(policy, metricKey, horizonMonths, ctrl.signal);
    pending
      .then((t) => {
        setTrace(t);
        setStatus("ready");
      })
      .catch((e: unknown) => {
        if (ctrl.signal.aborted) return;
        setError(e instanceof Error ? e.message : "Evidence unavailable");
        setStatus("error");
      });
    return () => ctrl.abort();
  }, [policy, metricKey, horizonMonths, example]);

  // Close on Escape.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div className="drawer-scrim" onClick={onClose}>
      <aside
        className="drawer"
        role="dialog"
        aria-modal="true"
        aria-label="Evidence trace"
        onClick={(e) => e.stopPropagation()}
      >
        <header className="drawer-head">
          <div>
            <span className="drawer-eyebrow">Evidence trace</span>
            <h2 className="drawer-title">
              {trace?.metric_label ?? metricKey ?? "Example evidence trace"}
            </h2>
          </div>
          <button
            type="button"
            className="drawer-close"
            onClick={onClose}
            aria-label="Close evidence drawer"
          >
            ✕
          </button>
        </header>

        <div className="drawer-body">
          {(example || !policy || !metricKey) && (
            <p className="brief-example-note">
              <span className="tag muted">Example</span>
              <span>
                the canonical §26 peak-transit metric on the §28 demo congestion
                charge — <strong>not</strong> a policy you compiled.
              </span>
            </p>
          )}

          {status === "loading" && (
            <div className="map-placeholder" style={{ height: "auto" }}>
              <span className="dot" /> <span>Tracing evidence…</span>
            </div>
          )}

          {status === "error" && (
            <div className="waiting">
              <span className="tag muted">Evidence unavailable</span>
              <p>{error}</p>
            </div>
          )}

          {trace && status === "ready" && <TraceView trace={trace} />}
        </div>
      </aside>
    </div>
  );
}

function TraceView({ trace }: { trace: ProvenanceTrace }) {
  const r = trace.result;
  const c = trace.confidence;
  return (
    <>
      <div className="drawer-meta">
        <span className={`tag ${trace.tag.toLowerCase()}`}>{trace.tag}</span>
        <span className="drawer-horizon">at {trace.horizon.label}</span>
        <span className="drawer-unit">{trace.unit}</span>
      </div>

      {/* Result: World A / B / Δ */}
      <section className="drawer-section">
        <div className="result-grid">
          <ResultCell label="World A" value={r.world_a} unit={trace.unit} />
          <ResultCell label="World B" value={r.world_b} unit={trace.unit} />
          <ResultCell
            label="Δ (policy effect)"
            value={r.delta}
            unit={trace.unit}
            emphasise
            pct={r.delta_pct}
          />
        </div>
        <p className="result-band">
          Δ uncertainty band {formatNumber(r.low)} – {formatNumber(r.high)}{" "}
          {trace.unit}
        </p>
      </section>

      {/* Confidence */}
      <section className="drawer-section">
        <h3 className="drawer-h3">Confidence at this horizon</h3>
        <div className="fm-prob" style={{ margin: "0.4rem 0" }}>
          <span className="fm-prob-label">confidence</span>
          <span className="fm-prob-bar" aria-hidden>
            <span
              className="fm-prob-fill"
              style={{ width: `${Math.round(c.value * 100)}%` }}
            />
          </span>
          <span className="fm-prob-val">{Math.round(c.value * 100)}%</span>
        </div>
        <p className="hint" style={{ marginTop: 0 }}>
          ± {formatNumber(c.band_half_width)} {trace.unit}
          {c.band_rel_pct != null
            ? ` (${c.band_rel_pct.toFixed(1)}% of |Δ|)`
            : ""}{" "}
          · {c.note}
        </p>
      </section>

      {/* Causal ladder (verbatim ASCII trace from the model) */}
      {trace.ascii_trace && (
        <section className="drawer-section">
          <h3 className="drawer-h3">Causal trace</h3>
          <pre className="ascii-trace">{trace.ascii_trace}</pre>
        </section>
      )}

      {/* Chain nodes */}
      {trace.chain.length > 0 && (
        <section className="drawer-section">
          <h3 className="drawer-h3">Chain · inputs → result</h3>
          <ol className="chain">
            {trace.chain.map((s, i) => (
              <ChainNode key={i} step={s} />
            ))}
          </ol>
        </section>
      )}

      {/* Behavioural rules / equations */}
      {trace.rules.length > 0 && (
        <section className="drawer-section">
          <h3 className="drawer-h3">Equations &amp; parameters</h3>
          <div className="rules">
            {trace.rules.map((rule) => (
              <RuleCard key={rule.name} rule={rule} />
            ))}
          </div>
        </section>
      )}

      {/* Assumptions */}
      {trace.assumptions.length > 0 && (
        <section className="drawer-section">
          <h3 className="drawer-h3">Assumptions</h3>
          <ul className="assump-list">
            {trace.assumptions.map((a) => (
              <AssumptionRow key={a.name} a={a} />
            ))}
          </ul>
        </section>
      )}

      {/* Historical analogues */}
      {trace.historical_analogues.length > 0 && (
        <section className="drawer-section">
          <h3 className="drawer-h3">Real-world analogues</h3>
          <p className="hint" style={{ marginTop: 0 }}>
            Illustrative context only — external real schemes, not a source of any
            simulated number here.
          </p>
          <div className="analogues">
            {trace.historical_analogues.map((h, i) => (
              <AnalogueCard key={i} h={h} />
            ))}
          </div>
        </section>
      )}

      {/* Citations */}
      {trace.citations.length > 0 && (
        <section className="drawer-section">
          <h3 className="drawer-h3">Citations</h3>
          <ul className="citation-list">
            {trace.citations.map((cit, i) => (
              <li key={i}>{cit}</li>
            ))}
          </ul>
        </section>
      )}

      <p className="hint drawer-note">{trace.note}</p>
    </>
  );
}

function ResultCell({
  label,
  value,
  unit,
  emphasise,
  pct,
}: {
  label: string;
  value: number;
  unit: string;
  emphasise?: boolean;
  pct?: number | null;
}) {
  return (
    <div className={`result-cell${emphasise ? " emphasise" : ""}`}>
      <span className="result-label">{label}</span>
      <span className="result-value">
        {formatNumber(value)}
        <span className="result-unit">{unit}</span>
      </span>
      {pct != null && (
        <span className="result-pct">{formatSignedPct(pct / 100)}</span>
      )}
    </div>
  );
}

function ChainNode({ step }: { step: TraceStep }) {
  return (
    <li className="chain-node">
      <span className={`chain-stage stage-${step.stage}`}>{step.stage}</span>
      <div className="chain-body">
        <div className="chain-node-head">
          <span className="chain-label">{step.label}</span>
          <span className={`tag ${step.tag.toLowerCase()}`}>{step.tag}</span>
        </div>
        <p className="chain-detail">{step.detail}</p>
        {step.value != null && (
          <span className="chain-value">
            {formatNumber(step.value)} {step.unit}
          </span>
        )}
      </div>
    </li>
  );
}

function RuleCard({ rule }: { rule: BehaviouralRule }) {
  const range =
    rule.plausible_range.length === 2
      ? `${formatNumber(rule.plausible_range[0])}–${formatNumber(rule.plausible_range[1])}`
      : null;
  return (
    <div className="rule-card">
      <div className="rule-head">
        <span className="rule-label">{rule.label}</span>
        <span className="rule-value">
          {formatNumber(rule.value)} {rule.unit}
        </span>
      </div>
      <p className="rule-param">{rule.parameter}</p>
      {rule.sensitivity && <p className="rule-sens">{rule.sensitivity}</p>}
      <div className="rule-foot">
        {range && <span className="rule-range">plausible {range}</span>}
        {rule.source && <span className="rule-source">{rule.source}</span>}
      </div>
    </div>
  );
}

function AssumptionRow({ a }: { a: TraceAssumption }) {
  return (
    <li className="assump-row">
      <div className="assump-main">
        <span className="assump-name">{a.name}</span>
        <span className="assump-value">
          {typeof a.value === "number" ? formatNumber(a.value) : a.value}
          {a.unit ? ` ${a.unit}` : ""}
        </span>
      </div>
      {a.detail && <span className="assump-detail">{a.detail}</span>}
    </li>
  );
}

function AnalogueCard({ h }: { h: HistoricalAnalogue }) {
  return (
    <div className="analogue-card">
      <div className="analogue-head">
        <span className="analogue-scheme">{h.scheme}</span>
        <span className="analogue-where">
          {h.city} · {h.year}
        </span>
        <span className="tag observed">Observed</span>
      </div>
      <p className="analogue-mech">{h.mechanism}</p>
      <p className="analogue-rel">{h.relevance}</p>
    </div>
  );
}
