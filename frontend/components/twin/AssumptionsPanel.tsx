"use client";

/**
 * Change-assumptions-and-rerun view (SPEC §34.10): the tenth product guardrail
 * made interactive. The §24 uncertainty fan *sweeps* the model's input
 * assumptions and ranks the most-influential one; this tab lets a user **pin any
 * of those same knobs to a chosen value and re-run the deterministic core** to
 * see exactly how much it moves the headline.
 *
 * Flow: `GET /assumptions` lists the overridable knobs (live from the code, so
 * the ranges can't drift from what runs); the user drags any slider off its
 * default to pin it; `POST /assumptions/rerun` re-runs the exact World-A/World-B/Δ
 * pipeline `/simulate` uses with those overrides, and returns a per-metric
 * contrast against the default-assumption run.
 *
 * Honesty (SPEC §34): no new numeric model and no LLM on the numeric path — the
 * re-run is the same deterministic core, so its Δ is Simulated. Input assumptions
 * are Estimated. Out-of-range values are clamped by the backend and flagged here
 * rather than silently used. When the backend is down we show a "waiting" state
 * and never fabricate a contrast.
 */

import { useEffect, useState } from "react";

import {
  getAssumptions,
  rerunAssumptions,
  UnknownAssumptionError,
} from "../../lib/api";
import type {
  AssumptionCard,
  AssumptionRerunResult,
  MetricContrast,
} from "../../lib/api";
import { formatNumber } from "../../lib/format";
import { useTwin } from "./TwinStore";

type CatStatus = "idle" | "loading" | "ready" | "error";
type RunStatus = "idle" | "loading" | "ready" | "error";

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

/** Signed compact number for display. */
function signed(v: number): string {
  return `${v > 0 ? "+" : v < 0 ? "−" : ""}${formatNumber(Math.abs(v))}`;
}

/** A sensible slider step for an assumption's range (≈120 stops). */
function stepFor(a: AssumptionCard): number {
  const span = a.high - a.low;
  if (span <= 0) return 0.01;
  const raw = span / 120;
  const mag = Math.pow(10, Math.floor(Math.log10(raw)));
  // Snap to 1/2/5 × 10^k so the readout stays tidy.
  const norm = raw / mag;
  const snap = norm >= 5 ? 5 : norm >= 2 ? 2 : 1;
  return snap * mag;
}

export default function AssumptionsPanel() {
  const { policy } = useTwin();
  const [catStatus, setCatStatus] = useState<CatStatus>("idle");
  const [cards, setCards] = useState<AssumptionCard[]>([]);
  const [catNote, setCatNote] = useState<string>("");
  const [catError, setCatError] = useState<string | null>(null);

  // name → pinned value. Absent = using the default (not sent as an override).
  const [pins, setPins] = useState<Record<string, number>>({});
  const [horizon, setHorizon] = useState(24);

  const [runStatus, setRunStatus] = useState<RunStatus>("idle");
  const [result, setResult] = useState<AssumptionRerunResult | null>(null);
  const [runError, setRunError] = useState<string | null>(null);

  // Load the catalogue once (it's static per backend build). Retryable on error.
  useEffect(() => {
    if (catStatus !== "idle") return;
    let alive = true;
    setCatStatus("loading");
    setCatError(null);
    getAssumptions()
      .then((c) => {
        if (!alive) return;
        setCards(c.assumptions);
        setCatNote(c.note);
        setCatStatus("ready");
      })
      .catch((e: unknown) => {
        if (!alive) return;
        setCatError(e instanceof Error ? e.message : "Could not load assumptions");
        setCatStatus("error");
      });
    return () => {
      alive = false;
    };
  }, [catStatus]);

  // A fresh/edited policy invalidates any prior re-run (but keeps the pins).
  useEffect(() => {
    setResult(null);
    setRunStatus("idle");
    setRunError(null);
  }, [policy]);

  const pinnedNames = Object.keys(pins);

  function setPin(name: string, value: number) {
    setPins((p) => ({ ...p, [name]: value }));
  }
  function unpin(name: string) {
    setPins((p) => {
      const next = { ...p };
      delete next[name];
      return next;
    });
  }
  function resetAll() {
    setPins({});
    setResult(null);
    setRunStatus("idle");
    setRunError(null);
  }

  async function rerun() {
    if (!policy || pinnedNames.length === 0) return;
    setRunStatus("loading");
    setRunError(null);
    try {
      const r = await rerunAssumptions(policy, pins, horizon);
      setResult(r);
      setRunStatus("ready");
    } catch (e: unknown) {
      if (e instanceof UnknownAssumptionError) {
        setRunError(
          `Backend rejected an assumption name. Overridable: ${e.overridable.join(", ")}`,
        );
      } else {
        setRunError(e instanceof Error ? e.message : "Re-run failed");
      }
      setRunStatus("error");
    }
  }

  return (
    <section className="card asm">
      <div className="dashboard-head">
        <h2>Change assumptions &amp; re-run</h2>
        <span className="dashboard-sub">
          Pin any input assumption and re-run the deterministic core (SPEC §34.10)
        </span>
      </div>

      {catStatus === "loading" && (
        <div className="waiting">
          <span className="tag muted">Loading</span>
          <p>Fetching the overridable-assumption catalogue…</p>
        </div>
      )}

      {catStatus === "error" && (
        <div className="waiting">
          <span className="tag muted">Waiting for backend</span>
          <p>
            Couldn’t reach the assumptions catalogue ({catError}). The knobs are
            read live from the running model, so nothing is shown until the
            backend answers — no fabricated defaults.
          </p>
          <button
            type="button"
            className="btn"
            onClick={() => setCatStatus("idle")}
          >
            Retry
          </button>
        </div>
      )}

      {catStatus === "ready" && (
        <>
          <p className="asm-intro">
            These are the <strong>same knobs the §24 uncertainty engine sweeps</strong>
            , read live from the code so the two can never disagree. Drag any
            slider off its default to pin it, then re-run — the contrast shows how
            much your change moved each metric’s Δ(B−A) versus the default-assumption
            run. <span className="tag estimated">Estimated</span> inputs →{" "}
            <span className="tag simulated">Simulated</span> outputs; no LLM touches
            the numeric path.
          </p>

          {!policy && (
            <div className="waiting asm-nopolicy">
              <span className="tag muted">No policy yet</span>
              <p>
                Compile a policy above to enable the re-run. You can still explore
                the knobs and their plausible ranges below.
              </p>
            </div>
          )}

          <div className="asm-controls">
            <label className="asm-horizon">
              <span className="asm-ctl-label">Contrast horizon</span>
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
            <div className="asm-actions">
              <span className="asm-pincount">
                {pinnedNames.length} pinned
              </span>
              <button
                type="button"
                className="btn"
                onClick={resetAll}
                disabled={pinnedNames.length === 0 && !result}
              >
                Reset
              </button>
              <button
                type="button"
                className="btn primary"
                onClick={rerun}
                disabled={!policy || pinnedNames.length === 0 || runStatus === "loading"}
              >
                {runStatus === "loading"
                  ? "Re-running…"
                  : result
                    ? "Re-run"
                    : "Re-run model"}
              </button>
            </div>
          </div>

          <div className="asm-knobs">
            {cards.map((a) => {
              const pinned = a.name in pins;
              const value = pinned ? pins[a.name] : a.default;
              const step = stepFor(a);
              return (
                <div
                  className={`asm-knob${pinned ? " pinned" : ""}`}
                  key={a.name}
                >
                  <div className="asm-knob-head">
                    <span className="asm-knob-label" title={`${a.target}.${a.field}`}>
                      {a.label}
                    </span>
                    {pinned ? (
                      <button
                        type="button"
                        className="asm-unpin"
                        onClick={() => unpin(a.name)}
                        title="Reset this knob to its default"
                      >
                        pinned ✕
                      </button>
                    ) : (
                      <span className="asm-knob-default">default</span>
                    )}
                  </div>
                  <div className="asm-knob-slider">
                    <span className="asm-edge">{formatNumber(a.low)}</span>
                    <input
                      type="range"
                      min={a.low}
                      max={a.high}
                      step={step}
                      value={value}
                      aria-label={`${a.label} (${a.low}…${a.high}${a.unit ? " " + a.unit : ""})`}
                      onChange={(e) => setPin(a.name, Number(e.target.value))}
                    />
                    <span className="asm-edge">{formatNumber(a.high)}</span>
                  </div>
                  <div className="asm-knob-foot">
                    <span className="asm-knob-value">
                      {formatNumber(value)}
                      {a.unit ? ` ${a.unit}` : ""}
                    </span>
                    <span className="asm-knob-vs">
                      default {formatNumber(a.default)}
                      {pinned && Math.abs(value - a.default) > 1e-9 && (
                        <em className="asm-knob-shift">
                          {" "}
                          ({signed(value - a.default)})
                        </em>
                      )}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>

          {catNote && <p className="hint asm-catnote">{catNote}</p>}

          {runStatus === "error" && (
            <p className="hint error-text asm-error">{runError}</p>
          )}

          {result && runStatus !== "loading" && <RerunResult r={result} />}
        </>
      )}
    </section>
  );
}

function RerunResult({ r }: { r: AssumptionRerunResult }) {
  const clampedAny = r.overrides.some((o) => o.clamped);
  return (
    <div className="asm-result">
      <div className="asm-result-head">
        <h3>Contrast at {r.horizon.label}</h3>
        <span className={`tag ${r.provenance.toLowerCase()}`}>{r.provenance}</span>
      </div>

      {/* What was actually applied (with clamp honesty). */}
      <div className="asm-applied">
        {r.overrides.map((o) => (
          <div
            className={`asm-applied-row${o.clamped ? " clamped" : ""}`}
            key={o.name}
          >
            <span className="asm-applied-label">{o.label}</span>
            <span className="asm-applied-vals">
              {formatNumber(o.default)}
              {o.unit ? ` ${o.unit}` : ""} → <strong>{formatNumber(o.applied)}
              {o.unit ? ` ${o.unit}` : ""}</strong>
              {o.clamped && (
                <span className="asm-clamp" title={o.note}>
                  clamped from {formatNumber(o.requested)}
                </span>
              )}
            </span>
          </div>
        ))}
      </div>

      {clampedAny && (
        <p className="hint asm-clamp-note">
          One or more requests fell outside the documented plausible range and were
          clamped to the edge (honest per SPEC §34) rather than silently used.
        </p>
      )}

      {/* Per-metric Δ(B−A): default assumptions vs your overrides. */}
      <ContrastTable contrast={r.contrast} />

      <p className="hint asm-note">{r.note}</p>
    </div>
  );
}

function ContrastTable({ contrast }: { contrast: MetricContrast[] }) {
  if (contrast.length === 0) {
    return <p className="hint">No metric contrast returned for this run.</p>;
  }
  // Scale the shift bars to the largest absolute shift in the table.
  const maxShift = Math.max(1e-9, ...contrast.map((c) => Math.abs(c.shift)));
  return (
    <div className="asm-contrast">
      <div className="asm-contrast-head">
        <span>Metric</span>
        <span>Δ default</span>
        <span>Δ overridden</span>
        <span>Shift (effect of your change)</span>
      </div>
      {contrast.map((c) => {
        const negligible = Math.abs(c.shift) < 1e-9;
        const good = c.shift > 0 === higherIsBetter(c.key);
        const cls = negligible ? "flat" : good ? "good" : "bad";
        const barPct = Math.min(100, (Math.abs(c.shift) / maxShift) * 100);
        return (
          <div className="asm-contrast-row" key={c.key}>
            <span className="asm-c-metric" title={c.key}>
              {c.label}
              {c.unit ? <em className="asm-c-unit"> ({c.unit})</em> : null}
            </span>
            <span className="asm-c-num">{signed(c.default_delta)}</span>
            <span className="asm-c-num">{signed(c.overridden_delta)}</span>
            <span className="asm-c-shift">
              <span className={`asm-shift-track ${cls}`}>
                <span
                  className="asm-shift-bar"
                  style={{ width: `${barPct}%` }}
                />
              </span>
              <span className={`asm-shift-val ${cls}`}>
                {negligible ? "≈ 0 (no change)" : signed(c.shift)}
                {!negligible && c.shift_pct_of_default != null && (
                  <em className="asm-shift-pct">
                    {" "}
                    ({c.shift_pct_of_default > 0 ? "+" : ""}
                    {c.shift_pct_of_default.toFixed(0)}%)
                  </em>
                )}
              </span>
            </span>
          </div>
        );
      })}
    </div>
  );
}
