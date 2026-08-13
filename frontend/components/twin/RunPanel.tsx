"use client";

/**
 * Run view (SPEC §28/§29 — the killer demo in one call).
 *
 * `POST /run` composes the entire engine — compile → simulate → public reaction
 * → parliament → amendment re-simulation → media — into a single, mutually-
 * consistent payload. The whole point of this tab (vs the per-layer tabs) is to
 * *show that consistency*: every section here reads the same compiled policy and
 * the same deterministic simulation, so the dashboard, parliament, amendment and
 * media can never disagree. It introduces no new numeric model.
 *
 * Honesty contract (SPEC §34): headline numbers are Simulated (read verbatim
 * from the shared run), debate/media prose is Generated, and no LLM touches any
 * figure. Nothing is fabricated — when the backend is down the panel says so and
 * offers a retry instead of inventing a narrative.
 */

import { useState } from "react";

import { runScenario } from "../../lib/api";
import type {
  DeltaSeries,
  RunHeadlineMetric,
  RunResponse,
} from "../../lib/api";
import { formatNumber } from "../../lib/format";
import { useTwin } from "./TwinStore";

type Status = "idle" | "loading" | "ready" | "error";

/** Horizon options snap to the Time-Machine checkpoints (SPEC §27). */
const HORIZONS: Array<{ label: string; months: number }> = [
  { label: "Year 1", months: 12 },
  { label: "Year 2", months: 24 },
  { label: "Year 5", months: 60 },
  { label: "Year 10", months: 120 },
];

/** Only transit ridership is "up = good"; everything else here is "down = good". */
function higherIsBetter(key: string): boolean {
  return key === "transit.daily_transit_trips";
}

export default function RunPanel() {
  const { policy } = useTwin();
  const [text, setText] = useState("");
  const [horizon, setHorizon] = useState(24);
  const [run, setRun] = useState<RunResponse | null>(null);
  const [status, setStatus] = useState<Status>("idle");
  const [error, setError] = useState<string | null>(null);

  // Prefer the compiled policy from the store; fall back to a natural-language
  // box so the tab can drive the whole compile→run pipeline standalone (SPEC §3).
  const usingText = !policy;

  function execute() {
    if (usingText && !text.trim()) return;
    setStatus("loading");
    setError(null);
    const req = usingText
      ? { text: text.trim(), horizon_months: horizon }
      : { policy: policy ?? undefined, horizon_months: horizon };
    runScenario(req)
      .then((r) => {
        setRun(r);
        setStatus("ready");
      })
      .catch((e: unknown) => {
        setError(e instanceof Error ? e.message : "Scenario run failed");
        setStatus("error");
      });
  }

  return (
    <section className="card run" data-tour="run">
      <div className="dashboard-head">
        <h2>Run · one-call pipeline</h2>
        <span className="dashboard-sub">
          compile → simulate → public → parliament → amendment → media, in a
          single mutually-consistent call (SPEC §28/§29)
        </span>
      </div>

      <p className="hint run-intro">
        Every section below reads the <strong>same</strong> compiled policy and
        the <strong>same</strong> simulation — the dashboard, parliament,
        amendment and media can&rsquo;t disagree. Numbers are Simulated;
        debate&nbsp;&amp; media prose is Generated; no LLM touches a figure.
      </p>

      {/* Input: compiled policy from the store, or a natural-language fallback. */}
      <div className="run-controls">
        {usingText ? (
          <label className="run-textwrap">
            <span className="run-label">
              No compiled policy yet — describe one to compile &amp; run:
            </span>
            <textarea
              className="run-text"
              rows={2}
              placeholder="e.g. Charge £12 to drive into the city centre at peak and spend it on buses"
              value={text}
              onChange={(e) => setText(e.target.value)}
            />
          </label>
        ) : (
          <p className="run-usingpolicy">
            <span className="tag generated">compiled policy</span>
            Running the pipeline for the policy compiled above.
          </p>
        )}

        <div className="run-actions">
          <label className="run-horizon">
            <span className="run-label">Dashboard horizon</span>
            <select
              value={horizon}
              onChange={(e) => setHorizon(Number(e.target.value))}
            >
              {HORIZONS.map((h) => (
                <option key={h.months} value={h.months}>
                  {h.label}
                </option>
              ))}
            </select>
          </label>
          <button
            type="button"
            className="btn primary"
            onClick={execute}
            disabled={status === "loading" || (usingText && !text.trim())}
          >
            {status === "loading"
              ? "Running pipeline…"
              : usingText
                ? "Compile & run"
                : "Run full pipeline"}
          </button>
        </div>
      </div>

      {status === "loading" && !run && (
        <p className="hint">
          Composing the killer-demo pipeline from the backend…
        </p>
      )}

      {status === "error" && (
        <div className="waiting">
          <span className="tag muted">Backend unavailable</span>
          <p>
            Couldn&rsquo;t run the scenario: {error}. Nothing here is invented —
            reconnect the backend to compose the pipeline (compile → simulate →
            parliament → amendment → media) from one deterministic run.
          </p>
          <button type="button" className="btn" onClick={execute}>
            Retry
          </button>
        </div>
      )}

      {run && <RunResult run={run} stale={status === "loading"} />}
    </section>
  );
}

function RunResult({ run, stale }: { run: RunResponse; stale: boolean }) {
  return (
    <div className={`run-result${stale ? " stale" : ""}`}>
      {stale && (
        <p className="hint run-stale">Re-running… showing the previous result.</p>
      )}

      {/* Consistency banner — the reason this tab exists. */}
      <div className="run-consistency">
        <div className="run-cons-tags">
          <span className="tag simulated">Numbers Simulated</span>
          <span className="tag generated">Prose Generated</span>
          <span className="tag observed">No LLM in numeric path</span>
        </div>
        <p className="run-cons-note">{run.note}</p>
      </div>

      {/* §29 storyline: each beat points at the evidence section. */}
      <h3 className="run-sub">The 60-second story</h3>
      <ol className="run-narrative">
        {run.narrative.map((b, i) => (
          <li className="run-beat" key={i}>
            <span className="run-beat-time">{b.timecode}</span>
            <div className="run-beat-body">
              <p className="run-beat-stage">
                {b.stage}
                <span className="run-beat-section">{b.section}</span>
              </p>
              <p className="run-beat-desc">{b.description}</p>
            </div>
          </li>
        ))}
      </ol>

      {/* Headline dashboard at the chosen horizon (Simulated). */}
      <h3 className="run-sub">
        Outcomes at {run.horizon_label}
        <span className="run-sub-tag">Simulated · Δ vs baseline</span>
      </h3>
      {run.headline.length > 0 ? (
        <div className="tiles run-tiles">
          {run.headline.map((m) => (
            <HeadlineTile key={m.key} m={m} />
          ))}
        </div>
      ) : (
        <p className="hint">No headline metrics returned for this horizon.</p>
      )}

      {/* Net public support (SPEC §13). */}
      <NetSupport value={run.net_support} />

      {/* Parliament snapshot — full debate lives in the Parliament tab. */}
      <h3 className="run-sub">
        Parliament
        <span className="run-sub-tag">Generated debate · Simulated citations</span>
      </h3>
      <div className="run-parliament">
        <p className="run-motion">“{run.parliament.motion}”</p>
        <div className="run-tally">
          {Object.entries(run.parliament.tally).map(([k, v]) => (
            <span className={`run-tally-pill ${k}`} key={k}>
              <span className="run-tally-n">{v}</span>
              <span className="run-tally-k">{k}</span>
            </span>
          ))}
        </div>
        <p className="run-summary">{run.parliament.summary}</p>
        <p className="hint run-xref">Full debate &amp; citations → Parliament tab.</p>
      </div>

      {/* Amendment (auto-derived or supplied) + isolated effect. */}
      <AmendmentBlock run={run} />

      {/* Simulated media — every headline stamped (SPEC §15). */}
      <h3 className="run-sub">
        Press
        <span className="run-sub-tag">Generated · fictional outlets</span>
      </h3>
      <div className="run-media">
        {run.media.scenarios.map((sc) => (
          <div className="run-media-scenario" key={sc.label}>
            <span className="run-media-when">{sc.label}</span>
            <ul className="run-media-list">
              {sc.headlines.slice(0, 3).map((h, i) => (
                <li className="run-media-item" key={i}>
                  <span className="tag simulated run-media-stamp">
                    {h.label || "SIMULATED"}
                  </span>
                  <span className="run-media-outlet">{h.outlet_label}</span>
                  <span className="run-media-head">{h.headline}</span>
                </li>
              ))}
            </ul>
          </div>
        ))}
        <p className="hint run-xref">
          {run.media.disclaimer} · full feed → Press tab.
        </p>
      </div>
    </div>
  );
}

function HeadlineTile({ m }: { m: RunHeadlineMetric }) {
  const negligible = m.direction === "flat" || Math.abs(m.delta) < 1e-9;
  const good = m.delta > 0 === higherIsBetter(m.key);
  const cls = negligible ? "muted" : good ? "down" : "up";
  return (
    <div className="tile">
      <div className="tile-head">
        <span className="tile-title" title={m.key}>
          {m.label}
        </span>
        <span className={`tag ${m.tag.toLowerCase()}`}>{m.tag}</span>
      </div>

      <div className="tile-value">
        {formatNumber(m.world_b)}
        <span className="tile-unit">{m.unit}</span>
      </div>

      <div className="tile-band">
        World A {formatNumber(m.world_a)} → B {formatNumber(m.world_b)}
      </div>
      <div className="tile-band">
        Δ band {formatNumber(m.band[0] ?? m.delta)}–
        {formatNumber(m.band[1] ?? m.delta)}
      </div>

      <div className="tile-deltas">
        <span className="delta">
          <span className="delta-label">vs baseline</span>
          <span className={`delta-val ${cls}`}>
            {negligible ? (
              "≈ 0"
            ) : (
              <>
                {m.delta > 0 ? "+" : ""}
                {formatNumber(m.delta)}
                {m.delta_pct != null
                  ? ` (${m.delta_pct > 0 ? "+" : ""}${m.delta_pct.toFixed(1)}%)`
                  : ""}
              </>
            )}
          </span>
        </span>
      </div>
    </div>
  );
}

/** Net public support gauge, value in [-1, 1] (SPEC §13). */
function NetSupport({ value }: { value: number }) {
  const pct = Math.max(-1, Math.min(1, value)) * 100;
  const positive = value >= 0;
  // Fill grows from the centre toward the sign's side.
  const half = Math.abs(pct) / 2; // % of the full bar width
  return (
    <div className="run-support">
      <div className="run-support-head">
        <span className="run-sub-inline">Net public support</span>
        <span className={`run-support-val ${positive ? "pos" : "neg"}`}>
          {value > 0 ? "+" : ""}
          {(value * 100).toFixed(0)}%
        </span>
        <span className="tag simulated">Simulated</span>
      </div>
      <div className="run-support-track" aria-hidden>
        <span className="run-support-mid" />
        <span
          className={`run-support-fill ${positive ? "pos" : "neg"}`}
          style={{
            left: positive ? "50%" : `${50 - half}%`,
            width: `${half}%`,
          }}
        />
      </div>
      <div className="run-support-scale" aria-hidden>
        <span>−100%</span>
        <span>0</span>
        <span>+100%</span>
      </div>
    </div>
  );
}

function AmendmentBlock({ run }: { run: RunResponse }) {
  const a = run.amendment;
  return (
    <>
      <h3 className="run-sub">
        Amendment
        <span className="run-sub-tag">
          {a.proposed ? "isolated effect · Simulated" : "none proposed"}
        </span>
      </h3>
      <div className="run-amendment">
        <p className="run-amd-source">
          <span className={`run-amd-pill ${a.proposed ? "on" : "off"}`}>
            {a.source}
          </span>
          {a.amendment ? a.amendment.label : "no structural amendment"}
        </p>
        <p className="run-amd-rationale">{a.rationale}</p>

        {a.comparison && (
          <AmendmentDelta series={a.comparison.amendment_delta.series} />
        )}
        {a.proposed && (
          <p className="hint run-xref">
            Amendment vs original policy, in full → Parliament tab.
          </p>
        )}
      </div>
    </>
  );
}

/** Δ(amended − original) at the final checkpoint per metric (SPEC §12). */
function AmendmentDelta({ series }: { series: DeltaSeries[] }) {
  const rows = series
    .map((s) => ({ s, p: s.points[s.points.length - 1] }))
    .filter((r) => r.p);
  if (rows.length === 0) return null;
  return (
    <div className="run-amd-table" role="table">
      <div className="run-amd-head" role="row">
        <span role="columnheader">Metric</span>
        <span role="columnheader" className="run-amd-num">
          Δ(amended − original)
        </span>
        <span role="columnheader" className="run-amd-band">
          band
        </span>
      </div>
      {rows.map(({ s, p }) => {
        const negligible = Math.abs(p.delta) < 1e-9;
        const dir = p.delta > 0 ? "up" : p.delta < 0 ? "down" : "flat";
        return (
          <div className="run-amd-row" role="row" key={s.key}>
            <span role="cell" className="run-amd-metric" title={s.key}>
              {s.label}
            </span>
            <span role="cell" className={`run-amd-num ${dir}`}>
              {negligible ? (
                <span className="run-amd-flat">≈ 0 (no change)</span>
              ) : (
                <>
                  {p.delta > 0 ? "+" : ""}
                  {formatNumber(p.delta)}
                  {p.delta_pct != null
                    ? ` (${p.delta_pct > 0 ? "+" : ""}${p.delta_pct.toFixed(1)}%)`
                    : ""}
                </>
              )}
            </span>
            <span role="cell" className="run-amd-band">
              {formatNumber(p.low)} … {formatNumber(p.high)}
            </span>
          </div>
        );
      })}
    </div>
  );
}
