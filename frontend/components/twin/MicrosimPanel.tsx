"use client";

/**
 * Distributional microsimulation view (SPEC §7.3): the policy's person-level
 * "who gains, who loses, by how much" — built by `POST /microsim` from each
 * synthetic commuter's change in minimum generalized cost between World A
 * (baseline) and World B (policy) under the same deterministic mode-choice model
 * as `/simulate`.
 *
 * Honesty story (SPEC §7.3/§34): the welfare change is Simulated (deterministic,
 * no LLM); the money-equivalent conversion uses a documented Estimated
 * value-of-time. The headline that matters most is the *regressivity gradient* —
 * whether the charge burden falls harder on lower incomes — so we surface it
 * prominently with the winners/losers split and per-decile / household /
 * geography / occupation breakdowns. When the backend is down we show a clear
 * waiting/error state; we never invent a distribution.
 */

import { useEffect, useState } from "react";

import { constraintVerdict, runMicrosim } from "../../lib/api";
import type {
  ConstraintCheck,
  GroupImpact,
  MicrosimReport,
} from "../../lib/api";
import { formatNumber } from "../../lib/format";
import { useTwin } from "./TwinStore";

type Status = "idle" | "loading" | "ready" | "error";

/** Signed minutes, e.g. +3.4 min worse / −1.2 min better. */
function mins(v: number): string {
  if (Math.abs(v) < 0.05) return "≈0";
  const sign = v > 0 ? "+" : "−";
  return `${sign}${Math.abs(v).toFixed(1)}`;
}

/** Signed money-equivalent (daily), £. */
function money(v: number): string {
  if (Math.abs(v) < 0.005) return "£0";
  const sign = v > 0 ? "+" : "−";
  return `${sign}£${formatNumber(Math.abs(v))}`;
}

function pct(v: number): string {
  return `${v.toFixed(0)}%`;
}

export default function MicrosimPanel() {
  const { policy } = useTwin();
  const [status, setStatus] = useState<Status>("idle");
  const [report, setReport] = useState<MicrosimReport | null>(null);
  const [error, setError] = useState<string | null>(null);

  // A fresh/edited policy invalidates any prior microsim run.
  useEffect(() => {
    setReport(null);
    setStatus("idle");
    setError(null);
  }, [policy]);

  async function run() {
    if (!policy) return;
    setStatus("loading");
    setError(null);
    try {
      const r = await runMicrosim(policy);
      setReport(r);
      setStatus("ready");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Microsimulation failed");
      setStatus("error");
    }
  }

  return (
    <section className="card microsim">
      <div className="dashboard-head">
        <h2>Distributional microsimulation</h2>
        <span className="dashboard-sub">
          Who gains, who loses · per-agent welfare + charge-burden gradient (SPEC §7.3)
        </span>
      </div>

      {!policy ? (
        <div className="waiting">
          <span className="tag muted">No policy yet</span>
          <p>
            Compile a policy above to see its person-level distribution — winners
            and losers by income decile, household type, neighbourhood and
            occupation, plus whether the charge burden is regressive.
          </p>
        </div>
      ) : (
        <>
          <div className="policy-actions" style={{ marginTop: 0 }}>
            <button
              type="button"
              className="btn primary"
              onClick={run}
              disabled={status === "loading"}
            >
              {status === "loading"
                ? "Simulating population…"
                : report
                  ? "Re-run microsim"
                  : "Run microsim"}
            </button>
            {report && (
              <span className="tag simulated">Simulated (money-equiv Estimated)</span>
            )}
          </div>

          {status === "error" && (
            <p className="hint error-text">Couldn&rsquo;t run microsim: {error}</p>
          )}

          {status === "idle" && !report && (
            <p className="hint">
              Runs the deterministic mode-choice model over the synthetic commuter
              population and measures each person&rsquo;s change in generalized cost
              (World B − World A). Welfare is Simulated; the money-equivalent uses a
              documented Estimated value-of-time. Click to run.
            </p>
          )}

          {report && status !== "loading" && (
            <div className="ms-body">
              <WinnersHeadline r={report} />
              {report.constraint_check && (
                <ConstraintCheckCard c={report.constraint_check} />
              )}
              <RegressivityCard r={report} />

              <GroupSection
                title="By income decile"
                note="the regressivity story — burden as % of income"
                groups={report.by_income_decile}
                showBurden
              />
              <GroupSection
                title="By household type"
                groups={report.by_household_type}
              />
              <GroupSection
                title="By home neighbourhood"
                groups={report.by_geography}
              />
              <GroupSection
                title="By occupation"
                groups={report.by_occupation}
              />

              {report.not_modelled.length > 0 && (
                <div className="eco-notmodelled">
                  <span className="eco-nm-title">Deliberately not modelled</span>
                  <ul>
                    {report.not_modelled.map((n, i) => (
                      <li key={i}>{n}</li>
                    ))}
                  </ul>
                </div>
              )}

              <ParamsBlock params={report.params} />

              <p className="hint eco-note">{report.note}</p>
            </div>
          )}
        </>
      )}
    </section>
  );
}

function WinnersHeadline({ r }: { r: MicrosimReport }) {
  const total = r.winners + r.losers + r.unaffected || 1;
  const wPct = (r.winners / total) * 100;
  const lPct = (r.losers / total) * 100;
  const uPct = (r.unaffected / total) * 100;
  return (
    <div className="ms-headline">
      <div className="ms-split">
        <div className="ms-split-nums">
          <span className="ms-winners">{formatNumber(r.winners)} better off</span>
          <span className="ms-losers">{formatNumber(r.losers)} worse off</span>
          <span className="ms-unaff">{formatNumber(r.unaffected)} unaffected</span>
        </div>
        <div
          className="ms-bar"
          role="img"
          aria-label={`${wPct.toFixed(0)}% better off, ${lPct.toFixed(0)}% worse off, ${uPct.toFixed(0)}% unaffected`}
        >
          <span className="ms-seg ms-seg-w" style={{ width: `${wPct}%` }} />
          <span className="ms-seg ms-seg-u" style={{ width: `${uPct}%` }} />
          <span className="ms-seg ms-seg-l" style={{ width: `${lPct}%` }} />
        </div>
        <div className="ms-split-meta">
          <span>{formatNumber(r.commuters)} commuters sampled</span>
          <span>
            mean per-trip change <strong>{mins(r.mean_gc_change_min)} min</strong>
          </span>
          <span className={`tag ${r.provenance.toLowerCase()}`}>{r.provenance}</span>
        </div>
      </div>
      {(r.biggest_winner || r.worst_hit) && (
        <div className="ms-named">
          {r.biggest_winner && (
            <span className="ms-named-win">
              <span className="ms-named-glyph good">▲</span> biggest winner:{" "}
              <strong>{r.biggest_winner}</strong>
            </span>
          )}
          {r.worst_hit && (
            <span className="ms-named-hit">
              <span className="ms-named-glyph warn">▼</span> worst hit:{" "}
              <strong>{r.worst_hit}</strong>
            </span>
          )}
        </div>
      )}
    </div>
  );
}

/**
 * "Did the policy keep its own promise?" — surfaces whether the policy's stated
 * `max_low_income_burden_increase_pct` cap actually holds against the modelled
 * low-income burden (SPEC §7.3/§34). A stated constraint the app never checks is
 * theatre; a violation is shown as a hard fail, never softened.
 */
function ConstraintCheckCard({ c }: { c: ConstraintCheck }) {
  const v = constraintVerdict(c);
  const glyph = v.status === "fail" ? "✕" : "✓";
  return (
    <div className={`ms-constraint ${v.cls}`}>
      <div className="ms-constraint-main">
        <span className={`ms-constraint-glyph ${v.cls}`} aria-hidden="true">
          {glyph}
        </span>
        <span className="ms-constraint-label">Stated equity constraint</span>
        <span className={`ms-constraint-verdict ${v.cls}`}>{v.label}</span>
        <span className={`tag ${c.provenance.toLowerCase()}`}>{c.provenance}</span>
      </div>
      <div className="ms-constraint-meta">
        <span>
          cap <strong>≤ {c.cap_pct.toFixed(2)}%</strong> of income
        </span>
        <span>
          modelled{" "}
          <strong>{c.modelled_low_income_burden_pct.toFixed(2)}%</strong>
        </span>
        <span className={v.status === "fail" ? "warn" : "good"}>
          {c.margin_pct >= 0
            ? `${c.margin_pct.toFixed(2)}pp headroom`
            : `${Math.abs(c.margin_pct).toFixed(2)}pp over`}
        </span>
      </div>
      {c.note && <p className="ms-constraint-note">{c.note}</p>}
    </div>
  );
}

function RegressivityCard({ r }: { r: MicrosimReport }) {
  const ratio = r.regressivity_ratio;
  // >1 regressive (burden heavier on low income); <1 progressive; ~0 no charge.
  const cls = ratio > 1.05 ? "warn" : ratio > 0 && ratio < 0.95 ? "good" : "mid";
  const verdict =
    ratio <= 0
      ? "no cordon charge burden"
      : ratio > 1.05
        ? "regressive"
        : ratio < 0.95
          ? "progressive"
          : "roughly flat";
  return (
    <div className={`ms-regress ${cls}`}>
      <div className="ms-regress-main">
        <span className="ms-regress-label">Charge-burden regressivity</span>
        <span className="ms-regress-value">
          {ratio > 0 ? `${ratio.toFixed(1)}×` : "—"}
        </span>
        <span className={`ms-regress-verdict ${cls}`}>{verdict}</span>
      </div>
      <div className="ms-regress-meta">
        <span>{formatNumber(r.payers)} charge payers</span>
        <span>
          mean payer burden <strong>{r.mean_payer_burden_pct.toFixed(2)}%</strong> of
          income
        </span>
      </div>
      {r.regressivity_note && (
        <p className="ms-regress-note">{r.regressivity_note}</p>
      )}
    </div>
  );
}

function GroupSection({
  title,
  note,
  groups,
  showBurden = false,
}: {
  title: string;
  note?: string;
  groups: GroupImpact[];
  showBurden?: boolean;
}) {
  if (!groups || groups.length === 0) return null;
  // Scale the welfare bar against the largest absolute mean change in this group.
  const maxAbs =
    Math.max(0.01, ...groups.map((g) => Math.abs(g.mean_gc_change_min))) || 1;
  return (
    <div className="ms-section">
      <h3 className="eco-sec-title">
        {title}
        {note && <span className="eco-sec-note">{note}</span>}
      </h3>
      <div className="ms-table" role="table" aria-label={title}>
        <div className="ms-row ms-row-head" role="row">
          <span role="columnheader">Group</span>
          <span role="columnheader">n</span>
          <span role="columnheader" title="Mean per-trip generalized-cost change">
            Δ cost
          </span>
          <span role="columnheader" title="Mean daily welfare change, money-equivalent">
            £/day
          </span>
          {showBurden && (
            <span role="columnheader" title="Annual charge as % of income">
              burden
            </span>
          )}
          <span role="columnheader" title="Share better / worse off">
            split
          </span>
        </div>
        {groups.map((g) => {
          const worse = g.mean_gc_change_min > 0;
          const barPct = Math.min(
            100,
            (Math.abs(g.mean_gc_change_min) / maxAbs) * 100,
          );
          return (
            <div className="ms-row" role="row" key={g.group}>
              <span className="ms-g-name" role="cell" title={g.group}>
                {g.group}
              </span>
              <span className="ms-g-n" role="cell">
                {formatNumber(g.agents)}
              </span>
              <span className="ms-g-cost" role="cell">
                <span className="ms-costbar-wrap">
                  <span
                    className={`ms-costbar ${worse ? "warn" : "good"}`}
                    style={{ width: `${barPct}%` }}
                  />
                </span>
                <span className={worse ? "warn" : "good"}>
                  {mins(g.mean_gc_change_min)}
                </span>
              </span>
              <span
                className={`ms-g-money ${g.mean_money_equiv_daily > 0 ? "warn" : "good"}`}
                role="cell"
              >
                {money(g.mean_money_equiv_daily)}
              </span>
              {showBurden && (
                <span className="ms-g-burden" role="cell">
                  {g.mean_burden_pct_income > 0
                    ? `${g.mean_burden_pct_income.toFixed(2)}%`
                    : "—"}
                </span>
              )}
              <span className="ms-g-split" role="cell">
                <span className="good" title="better off">
                  {pct(g.pct_better_off)}
                </span>
                {" / "}
                <span className="warn" title="worse off">
                  {pct(g.pct_worse_off)}
                </span>
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function ParamsBlock({ params }: { params: Record<string, unknown> }) {
  const entries = Object.entries(params ?? {});
  if (entries.length === 0) return null;
  return (
    <details className="eco-assumptions">
      <summary>
        Model assumptions <span className="eco-assum-count">({entries.length})</span>
      </summary>
      <dl>
        {entries.map(([k, v]) => (
          <div key={k} className="eco-assum-row">
            <dt>{k.replace(/_/g, " ")}</dt>
            <dd>{typeof v === "object" ? JSON.stringify(v) : String(v)}</dd>
          </div>
        ))}
      </dl>
    </details>
  );
}
