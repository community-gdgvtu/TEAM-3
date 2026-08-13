"use client";

/**
 * Twin workspace: composes the 3D map, the Time Machine scrubber and (M4.4) the
 * outcomes dashboard, sharing a single selected-checkpoint state so scrubbing the
 * timeline drives both the map time badge and the dashboard tiles.
 *
 * The baseline (World A) time series comes from `GET /baseline`. If the backend
 * is not live the map still renders (geometry is bundled), and the timeline shows
 * a clear "waiting for backend" state rather than inventing numbers (SPEC §34).
 */

import { useEffect, useState } from "react";

import { getBaseline } from "../../lib/api";
import type { BaselineResponse } from "../../lib/api";
import CityMapPanel from "../map/CityMapPanel";
import TimelineScrubber from "./TimelineScrubber";
import Dashboard from "./Dashboard";

export default function TwinWorkspace() {
  const [baseline, setBaseline] = useState<BaselineResponse | null>(null);
  const [status, setStatus] = useState<"loading" | "ready" | "waiting">(
    "loading",
  );
  const [index, setIndex] = useState(0);

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

  const checkpoints = baseline?.timeseries.checkpoints ?? [];
  const timeLabel = checkpoints[index]?.label;

  return (
    <div className="twin">
      <CityMapPanel timeLabel={status === "ready" ? timeLabel : undefined} />

      <section className="card timeline-card">
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
          <TimelineScrubber
            checkpoints={checkpoints}
            index={index}
            onChange={setIndex}
          />
        )}
      </section>

      {status === "ready" && baseline && (
        <Dashboard timeseries={baseline.timeseries} index={index} />
      )}
    </div>
  );
}
