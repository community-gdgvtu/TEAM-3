"use client";

/**
 * Economic spillover view (SPEC §7.4): the policy's local-economy impact, built
 * by `POST /economy` as a transparent partial-equilibrium translation of the
 * deterministic mode-choice simulation.
 *
 * The honesty story this panel tells (SPEC §7.4/§8/§34): this is NOT a GDP figure
 * and NOT a Simulated core output. Each transmission channel names the *Simulated*
 * physical driver it reads (mode shift, charge revenue, travel-cost change) and
 * the elasticity/IO assumption that *Estimates* the money from it — two distinct
 * provenance classes, both surfaced. The net figure carries a wide band and the
 * panel is explicit about the effects it deliberately does not model. No LLM
 * touches any number; when the backend is down we show an honest waiting/error
 * state rather than inventing a figure.
 */

import { useEffect, useState } from "react";

import { runEconomy } from "../../lib/api";
import type {
  EconomicChannel,
  EconomicSpilloverReport,
  SectorExposure,
} from "../../lib/api";
import { formatNumber } from "../../lib/format";
import { useTwin } from "./TwinStore";

type Status = "idle" | "loading" | "ready" | "error";

/** Signed compact currency, e.g. +1.2M / −340.0k / 0. */
function money(v: number): string {
  if (v === 0) return "0";
  const sign = v > 0 ? "+" : "−";
  return `${sign}${formatNumber(Math.abs(v))}`;
}

const DIR_CLASS: Record<string, string> = {
  positive: "good",
  negative: "warn",
  ambiguous: "mid",
};

const DIR_GLYPH: Record<string, string> = {
  positive: "▲",
  negative: "▼",
  ambiguous: "◆",
};

const MAG_LABEL: Record<string, string> = {
  low: "low exposure",
  moderate: "moderate exposure",
  high: "high exposure",
};

export default function EconomyPanel() {
  const { policy } = useTwin();
  const [status, setStatus] = useState<Status>("idle");
  const [report, setReport] = useState<EconomicSpilloverReport | null>(null);
  const [error, setError] = useState<string | null>(null);

  // A fresh/edited policy invalidates any prior economy run.
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
      const r = await runEconomy(policy);
      setReport(r);
      setStatus("ready");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Economy model failed");
      setStatus("error");
    }
  }

  return (
    <section className="card economy">
      <div className="dashboard-head">
        <h2>Economic spillover</h2>
        <span className="dashboard-sub">
          Local-economy channels · partial-equilibrium, band = uncertainty (SPEC §7.4)
        </span>
      </div>

      {!policy ? (
        <div className="waiting">
          <span className="tag muted">No policy yet</span>
          <p>
            Compile a policy above to translate its Simulated mode shifts and
            charge revenue into transparent local-economy channels — with a net
            annual estimate, a wide band, and an explicit list of what isn&rsquo;t
            modelled.
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
                ? "Translating channels…"
                : report
                  ? "Re-run spillover"
                  : "Run spillover"}
            </button>
            {report && (
              <span className="tag estimated">Estimated (from Simulated drivers)</span>
            )}
          </div>

          {status === "error" && (
            <p className="hint error-text">Couldn&rsquo;t run spillover: {error}</p>
          )}

          {status === "idle" && !report && (
            <p className="hint">
              Reads the deterministic simulation&rsquo;s physical outputs (mode
              shifts, cordon revenue, travel-cost changes) and applies documented
              elasticity / input-output assumptions to Estimate a net local
              economic effect. Click to run.
            </p>
          )}

          {report && status !== "loading" && (
            <div className="eco-body">
              <NetHeadline r={report} />

              <h3 className="eco-sec-title">
                Transmission channels{" "}
                <span className="eco-sec-note">
                  physical driver <span className="tag simulated">Simulated</span> →
                  money <span className="tag estimated">Estimated</span>
                </span>
              </h3>
              <div className="eco-channels">
                {report.channels.map((c) => (
                  <ChannelRow key={c.id} c={c} unit={report.unit} />
                ))}
                {report.channels.length === 0 && (
                  <p className="hint">
                    No quantifiable channel fired for this intervention.
                  </p>
                )}
              </div>

              {report.sector_exposure.length > 0 && (
                <>
                  <h3 className="eco-sec-title">
                    Sector exposure{" "}
                    <span className="eco-sec-note">direction &amp; magnitude, not hard jobs numbers</span>
                  </h3>
                  <div className="eco-sectors">
                    {report.sector_exposure.map((s) => (
                      <SectorCard key={s.sector} s={s} />
                    ))}
                  </div>
                </>
              )}

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

              <AssumptionsBlock assumptions={report.assumptions} />

              <p className="hint eco-note">{report.note}</p>
            </div>
          )}
        </>
      )}
    </section>
  );
}

function NetHeadline({ r }: { r: EconomicSpilloverReport }) {
  const dirClass = r.net_annual_impact > 0 ? "good" : r.net_annual_impact < 0 ? "warn" : "mid";
  const confPct = Math.round(r.net_confidence * 100);
  return (
    <div className="eco-net">
      <div className="eco-net-main">
        <span className={`eco-net-value ${dirClass}`}>{money(r.net_annual_impact)}</span>
        <span className="eco-net-unit">{r.unit}</span>
      </div>
      <div className="eco-net-meta">
        <span className="eco-net-band">
          band {money(r.net_annual_impact_low)} … {money(r.net_annual_impact_high)}
        </span>
        <span className="eco-net-conf" title="Confidence in the net estimate">
          confidence {confPct}%
        </span>
        <span className="eco-net-horizon">at {r.horizon.label}</span>
        <span className={`tag ${r.provenance.toLowerCase()}`}>{r.provenance}</span>
      </div>
      {r.headline && <p className="eco-headline">{r.headline}</p>}
    </div>
  );
}

function ChannelRow({ c, unit }: { c: EconomicChannel; unit: string }) {
  const dc = DIR_CLASS[c.direction] ?? "mid";
  const confPct = Math.round(c.confidence * 100);
  return (
    <div className="eco-channel">
      <div className="eco-ch-head">
        <span className={`eco-dir ${dc}`} title={c.direction}>
          {DIR_GLYPH[c.direction] ?? "◆"}
        </span>
        <span className="eco-ch-name">{c.name}</span>
        <span className="eco-ch-impact">
          {money(c.annual_impact)}
          <span className="eco-ch-band">
            {" "}
            ({money(c.annual_impact_low)} … {money(c.annual_impact_high)})
          </span>
        </span>
        <span className={`tag ${c.tag.toLowerCase()}`}>{c.tag}</span>
      </div>

      <p className="eco-ch-mech">{c.mechanism}</p>

      <div className="eco-ch-basis">
        <span className="eco-basis-label">
          <span className="tag simulated">Simulated</span> driver
        </span>
        <span className="eco-basis-val">
          {c.physical_basis}
          {c.physical_value != null && (
            <> = <strong>{formatNumber(c.physical_value)}</strong></>
          )}
        </span>
        <span className="eco-ch-conf" title="Confidence in this channel">
          {c.confidence_label || "confidence"} {confPct}%
        </span>
      </div>

      {c.assumptions.length > 0 && (
        <ul className="eco-ch-assumptions">
          {c.assumptions.map((a, i) => (
            <li key={i}>{a}</li>
          ))}
        </ul>
      )}
      {c.note && <p className="eco-ch-note">{c.note}</p>}
    </div>
  );
}

function SectorCard({ s }: { s: SectorExposure }) {
  const dc = DIR_CLASS[s.direction] ?? "mid";
  return (
    <div className="eco-sector">
      <div className="eco-sector-head">
        <span className={`eco-dir ${dc}`} title={s.direction}>
          {DIR_GLYPH[s.direction] ?? "◆"}
        </span>
        <span className="eco-sector-name">{s.sector.replace(/_/g, " ")}</span>
        <span className={`eco-mag eco-mag-${s.magnitude}`}>
          {MAG_LABEL[s.magnitude] ?? s.magnitude}
        </span>
      </div>
      <p className="eco-sector-mech">{s.mechanism}</p>
      {s.annual_impact_estimate != null && (
        <span className="eco-sector-est">
          ≈ {money(s.annual_impact_estimate)}{" "}
          <span className={`tag ${s.tag.toLowerCase()}`}>{s.tag}</span>
        </span>
      )}
    </div>
  );
}

function AssumptionsBlock({ assumptions }: { assumptions: Record<string, unknown> }) {
  const entries = Object.entries(assumptions ?? {});
  if (entries.length === 0) return null;
  return (
    <details className="eco-assumptions">
      <summary>
        Translation assumptions <span className="eco-assum-count">({entries.length})</span>
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
