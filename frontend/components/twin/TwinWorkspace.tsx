"use client";

/**
 * Twin workspace: composes the 3D map, the Time Machine scrubber and the outcomes
 * dashboard, sharing a single selected-checkpoint state so scrubbing drives both
 * the map time badge and the dashboard tiles.
 *
 * The baseline (World A) time series comes from `GET /baseline`. When a policy is
 * compiled it can be simulated (`POST /simulate`) — the dashboard then shows
 * World B + Δ vs baseline. Amendments applied in the parliament re-simulate into
 * the same shared state, so the dashboard updates from here too (SPEC §29). If the
 * backend is down the map still renders and no numbers are invented (SPEC §34).
 */

import { useEffect, useState } from "react";

import { getBaseline, simulate } from "../../lib/api";
import type { BaselineResponse } from "../../lib/api";
import CityMapPanel from "../map/CityMapPanel";
import TimelineScrubber from "./TimelineScrubber";
import Dashboard from "./Dashboard";
import EvidenceDrawer from "./EvidenceDrawer";
import { useTwin } from "./TwinStore";

export default function TwinWorkspace() {
  const { policy, sim, simSource, setSim } = useTwin();
  const [baseline, setBaseline] = useState<BaselineResponse | null>(null);
  const [status, setStatus] = useState<"loading" | "ready" | "waiting">(
    "loading",
  );
  const [index, setIndex] = useState(0);
  const [simulating, setSimulating] = useState(false);
  const [simError, setSimError] = useState<string | null>(null);
  const [explainKey, setExplainKey] = useState<string | null>(null);

  useEffect(() => {
    const ctrl = new AbortController();
    getBaseline(ctrl.signal)
      .then((b) => {
        setBaseline(b);
        setStatus("ready");
      })
      .catch(() => {
        if (ctrl.signal.aborted) return;
        setStatus("waiting");
      });
    return () => ctrl.abort();
  }, []);

  async function runSimulation() {
    if (!policy) return;
    setSimulating(true);
    setSimError(null);
    try {
      const result = await simulate(policy);
      setSim(result, { label: "Original policy", amended: false });
    } catch (e: unknown) {
      setSimError(e instanceof Error ? e.message : "Simulation failed");
    } finally {
      setSimulating(false);
    }
  }

  const checkpoints = baseline?.timeseries.checkpoints ?? [];
  const timeLabel = checkpoints[index]?.label;
  const mapTime =
    status === "ready" && timeLabel
      ? sim
        ? `World B · ${timeLabel}`
        : timeLabel
      : undefined;

  return (
    <div className="twin">
      {/* SPEC §27: 3D world (left) + outcomes (right). */}
      <div className="twin-top">
        <CityMapPanel timeLabel={mapTime} />

        {status === "ready" && baseline ? (
          <Dashboard
            timeseries={baseline.timeseries}
            index={index}
            sim={sim}
            simSource={simSource}
            onExplain={policy ? setExplainKey : undefined}
          />
        ) : (
          <section className="card dashboard" data-tour="outcomes">
            <div className="dashboard-head">
              <h2>Outcomes</h2>
              <span className="dashboard-sub">
                Traffic · CO₂ · Transit · Equity · Support
              </span>
            </div>
            {status === "loading" ? (
              <div className="map-placeholder" style={{ height: "auto" }}>
                <span className="dot" /> <span>Loading baseline…</span>
              </div>
            ) : (
              <div className="waiting">
                <span className="tag muted">Waiting for backend</span>
                <p>
                  Outcomes need the World-A baseline from{" "}
                  <code>GET /baseline</code>. No numbers are shown until the model
                  responds (SPEC §34).
                </p>
              </div>
            )}
          </section>
        )}
      </div>

      {/* SPEC §27: draggable timeline spans the full width below the two panels. */}
      <section className="card timeline-card" data-tour="timeline">
        {status === "loading" && (
          <div className="map-placeholder" style={{ height: "auto" }}>
            <span className="dot" /> <span>Loading baseline…</span>
          </div>
        )}
        {status === "waiting" && (
          <div className="waiting">
            <span className="tag muted">Waiting for backend</span>
            <p>
              The Time Machine needs the World-A baseline from{" "}
              <code>GET /baseline</code>. Start the backend to project traffic,
              CO₂ and transit across the T0 → 10-year horizon. No numbers are
              shown until the model responds (SPEC §34).
            </p>
          </div>
        )}
        {status === "ready" && baseline && (
          <>
            <TimelineScrubber
              checkpoints={checkpoints}
              index={index}
              onChange={setIndex}
            />
            <div className="sim-bar">
              <button
                type="button"
                className="btn primary"
                onClick={runSimulation}
                disabled={!policy || simulating}
                title={policy ? "Run World B" : "Compile a policy first"}
              >
                {simulating
                  ? "Simulating…"
                  : sim
                    ? "Re-simulate policy"
                    : "Run counterfactual"}
              </button>
              {sim && (
                <>
                  <span className="tag simulated">
                    World B · {simSource?.label ?? "policy"}
                  </span>
                  <button
                    type="button"
                    className="btn"
                    onClick={() => setSim(null, null)}
                  >
                    Show baseline
                  </button>
                </>
              )}
              {!policy && (
                <span className="hint" style={{ margin: 0 }}>
                  Compile a policy above to run the counterfactual (World B).
                </span>
              )}
              {simError && <span className="error-text">{simError}</span>}
            </div>
          </>
        )}
      </section>

      {policy && explainKey && (
        <EvidenceDrawer
          policy={policy}
          metricKey={explainKey}
          horizonMonths={checkpoints[index]?.t_months}
          onClose={() => setExplainKey(null)}
        />
      )}
    </div>
  );
}
