"use client";

/**
 * Outcomes dashboard (SPEC §27): the five headline tiles — Traffic, CO₂,
 * Transit, Equity burden, Support — at the selected Time Machine checkpoint.
 *
 * When no simulation is active the tiles show the World-A baseline. Once a policy
 * (or an amendment) is simulated, `sim` supplies Δ(B−A) per metric and the tiles
 * flip to World B + the real policy effect vs baseline — this is what "apply
 * amendment + re-simulate" updates (SPEC §29). Equity and Support have no series
 * yet, so they stay explicit "awaiting /simulate" placeholders (SPEC §34).
 */

import { useMemo } from "react";

import type {
  BaselineTimeSeries,
  DeltaSeries,
  MetricSeries,
  SimulateResponse,
} from "../../lib/api";
import type { SimSource } from "./TwinStore";
import MetricTile from "./MetricTile";

export interface DashboardProps {
  timeseries: BaselineTimeSeries;
  index: number;
  sim: SimulateResponse | null;
  simSource: SimSource | null;
}

interface TileSpec {
  title: string;
  key: string | null;
  color: string;
  higherIsBetter?: boolean;
  placeholderNote?: string;
}

const TILES: TileSpec[] = [
  { title: "Traffic", key: "traffic.daily_vehicle_km", color: "#4f8cff" },
  { title: "CO₂", key: "emissions.daily_co2_tonnes", color: "#f6be60" },
  {
    title: "Transit",
    key: "transit.daily_transit_trips",
    color: "#3ddc97",
    higherIsBetter: true,
  },
  {
    title: "Equity burden",
    key: null,
    color: "#c98bff",
    placeholderNote:
      "Distributional burden by income/geography comes from the policy + public-reaction model (/simulate).",
  },
  {
    title: "Support",
    key: null,
    color: "#ff8db0",
    placeholderNote:
      "Cohort support/opposition comes from the public-reaction model (/simulate).",
  },
];

export default function Dashboard({
  timeseries,
  index,
  sim,
  simSource,
}: DashboardProps) {
  const byKey = useMemo(() => {
    const m = new Map<string, MetricSeries>();
    for (const s of timeseries.series) m.set(s.key, s);
    return m;
  }, [timeseries]);

  const deltaByKey = useMemo(() => {
    const m = new Map<string, DeltaSeries>();
    if (sim) for (const s of sim.delta.series) m.set(s.key, s);
    return m;
  }, [sim]);

  return (
    <section className="card dashboard">
      <div className="dashboard-head">
        <h2>Outcomes</h2>
        <span className="dashboard-sub">
          {sim
            ? `World B (${simSource?.label ?? "policy"}) vs baseline · Δ shown at the selected horizon`
            : "World A (baseline) at the selected horizon · uncertainty band widens with time"}
        </span>
      </div>

      {sim && simSource?.amended && (
        <div className="overlay-banner">
          <span className="tag simulated">Amended</span>
          <span className="overlay-caption">
            Showing the re-simulated <strong>{simSource.label}</strong>. Δ is the
            amended policy vs the World-A baseline.
          </span>
        </div>
      )}

      <div className="tiles">
        {TILES.map((t) => (
          <MetricTile
            key={t.title}
            title={t.title}
            series={t.key ? byKey.get(t.key) ?? null : null}
            delta={t.key ? deltaByKey.get(t.key) ?? null : null}
            index={index}
            color={t.color}
            higherIsBetter={t.higherIsBetter}
            placeholderNote={t.placeholderNote}
          />
        ))}
      </div>
    </section>
  );
}
