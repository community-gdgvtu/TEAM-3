"use client";

/**
 * Client wrapper for the 3D city map.
 *
 * The map (MapLibre + deck.gl) touches `window` at import, so it is dynamically
 * imported with SSR disabled. This wrapper owns geometry loading + loading/empty/
 * error states, the choropleth-metric switcher, the legend, and the provenance
 * stamp (the geometry is Synthetic world input, SPEC §34).
 */

import dynamic from "next/dynamic";
import { useEffect, useMemo, useState } from "react";

import { loadCityGeometry } from "../../lib/city";
import type { CityGeometry } from "../../lib/city";
import type { ChoroplethMetric } from "./CityMap";

const CityMap = dynamic(() => import("./CityMap"), {
  ssr: false,
  loading: () => <MapPlaceholder label="Loading map engine…" />,
});

const METRICS: Array<{ key: ChoroplethMetric; label: string }> = [
  { key: "population", label: "Residents" },
  { key: "jobs", label: "Jobs" },
  { key: "job_density", label: "Job density" },
];

function MapPlaceholder({ label }: { label: string }) {
  return (
    <div className="map-placeholder">
      <span className="dot" />
      <span>{label}</span>
    </div>
  );
}

export default function CityMapPanel() {
  const [geometry, setGeometry] = useState<CityGeometry | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [metric, setMetric] = useState<ChoroplethMetric>("population");
  const [extruded, setExtruded] = useState(true);

  useEffect(() => {
    const ctrl = new AbortController();
    loadCityGeometry(ctrl.signal)
      .then(setGeometry)
      .catch((e: unknown) => {
        if (ctrl.signal.aborted) return;
        setError(e instanceof Error ? e.message : "Failed to load city geometry");
      });
    return () => ctrl.abort();
  }, []);

  const totals = useMemo(() => geometry?.manifest.totals ?? {}, [geometry]);

  return (
    <section className="map-section card">
      <div className="map-header">
        <div>
          <h2>Meridia — 3D world</h2>
          <p className="map-sub">
            {geometry
              ? `${geometry.manifest.counts.zones} zones · ${geometry.manifest.counts.roads} links · CBD cordon`
              : "Synthetic city grid"}
          </p>
        </div>
        <div className="map-controls">
          <div className="seg" role="group" aria-label="Colour zones by">
            {METRICS.map((m) => (
              <button
                key={m.key}
                className={`seg-btn${metric === m.key ? " active" : ""}`}
                onClick={() => setMetric(m.key)}
                type="button"
              >
                {m.label}
              </button>
            ))}
          </div>
          <label className="switch">
            <input
              type="checkbox"
              checked={extruded}
              onChange={(e) => setExtruded(e.target.checked)}
            />
            3D
          </label>
        </div>
      </div>

      <div className="map-canvas">
        {error ? (
          <MapPlaceholder label={`Map unavailable — ${error}`} />
        ) : !geometry ? (
          <MapPlaceholder label="Loading Meridia…" />
        ) : (
          <CityMap geometry={geometry} colorMetric={metric} extruded={extruded} />
        )}
      </div>

      <div className="map-footer">
        <div className="map-legend">
          <span className="legend-label">Low</span>
          <span className="legend-ramp" aria-hidden />
          <span className="legend-label">High</span>
          <span className="legend-item">
            <span className="swatch cordon" /> CBD cordon
          </span>
          <span className="legend-item">
            <span className="swatch cross" /> Cordon-crossing road
          </span>
        </div>
        <div className="map-provenance">
          <span className="tag muted">Synthetic</span>
          <span>
            World input — not a simulation result. Policy effects come from{" "}
            <code>/simulate</code>.
          </span>
        </div>
      </div>

      {geometry && (
        <dl className="kv map-totals">
          <dt>Population</dt>
          <dd>{(totals.population ?? 0).toLocaleString()}</dd>
          <dt>Jobs</dt>
          <dd>{(totals.jobs ?? 0).toLocaleString()}</dd>
          <dt>Daily trips into CBD</dt>
          <dd>{(totals.daily_trips_into_cbd ?? 0).toLocaleString()}</dd>
        </dl>
      )}
    </section>
  );
}
