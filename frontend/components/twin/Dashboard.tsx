"use client";

/**
 * Outcomes dashboard (SPEC §27): the five headline tiles — Traffic, CO₂,
 * Transit, Equity burden, Support — at the selected Time Machine checkpoint.
 *
 * Traffic / CO₂ / Transit map to World-A baseline series. Equity and Support
 * have no baseline series (they emerge from the policy + public-reaction model),
 * so they render an explicit "awaiting /simulate" placeholder rather than an
 * invented number (SPEC §34).
 */

import { useMemo } from "react";

import type { BaselineTimeSeries, MetricSeries } from "../../lib/api";
import MetricTile from "./MetricTile";

export interface DashboardProps {
  timeseries: BaselineTimeSeries;
  index: number;
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

export default function Dashboard({ timeseries, index }: DashboardProps) {
  const byKey = useMemo(() => {
    const m = new Map<string, MetricSeries>();
    for (const s of timeseries.series) m.set(s.key, s);
    return m;
  }, [timeseries]);

  return (
    <section className="card dashboard">
      <div className="dashboard-head">
        <h2>Outcomes</h2>
        <span className="dashboard-sub">
          World A (baseline) at the selected horizon · uncertainty band widens
          with time
        </span>
      </div>
      <div className="tiles">
        {TILES.map((t) => (
          <MetricTile
            key={t.title}
            title={t.title}
            series={t.key ? byKey.get(t.key) ?? null : null}
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
