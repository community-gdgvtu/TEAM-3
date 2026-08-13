"use client";

/**
 * The simple simulator: pick a scenario, drag ten years, watch the city change.
 *
 * This is the whole default experience. It owns three pieces of state — the
 * chosen scenario, the year on the scrubber, and whether the OD flow arcs are
 * drawn — and everything else is derived. The prediction model runs in the
 * browser (`lib/cityModel.ts`) so scrubbing is instant and the demo survives the
 * backend being down; the full agent-based engine, the uncertainty bands, the
 * parliament and the press stay one click away under "Advanced".
 */

import dynamic from "next/dynamic";
import { useEffect, useMemo, useRef, useState } from "react";

import { loadCityScene } from "../../lib/city";
import type { SceneData } from "../../lib/city";
import {
  BASELINE_SCENARIO,
  SCENARIOS,
  cityConstants,
  deltaPct,
  predict,
} from "../../lib/cityModel";
import type { Scenario } from "../../lib/cityModel";
import SourcesNote from "./SourcesNote";

const CityCanvas = dynamic(() => import("./CityCanvas"), {
  ssr: false,
  loading: () => <SceneMessage label="Starting the 3D engine…" />,
});

function SceneMessage({ label }: { label: string }) {
  return (
    <div className="scene-message">
      <span className="dot" />
      <span>{label}</span>
    </div>
  );
}

/** Whole years the scrubber snaps its labels to. */
const YEAR_TICKS = [0, 2, 4, 6, 8, 10];

function yearLabel(y: number): string {
  if (y < 0.05) return "Today";
  if (y < 1) return `${Math.round(y * 12)} months`;
  return `Year ${y.toFixed(1).replace(/\.0$/, "")}`;
}

function fmt(n: number, digits = 0): string {
  return n.toLocaleString(undefined, {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

function Delta({ pct, goodWhenDown }: { pct: number | null; goodWhenDown: boolean }) {
  if (pct === null || Math.abs(pct) < 0.05) {
    return <span className="delta flat">— vs do nothing</span>;
  }
  const good = goodWhenDown ? pct < 0 : pct > 0;
  return (
    <span className={`delta ${good ? "good" : "bad"}`}>
      {pct > 0 ? "▲" : "▼"} {Math.abs(pct).toFixed(1)}% vs do nothing
    </span>
  );
}

export default function CityStudio() {
  const [scene, setScene] = useState<SceneData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [scenario, setScenario] = useState<Scenario>(BASELINE_SCENARIO);
  const [year, setYear] = useState(0);
  const [showFlows, setShowFlows] = useState(true);
  const [playing, setPlaying] = useState(false);
  const raf = useRef<number | null>(null);

  useEffect(() => {
    const ctrl = new AbortController();
    loadCityScene(ctrl.signal)
      .then(setScene)
      .catch((e: unknown) => {
        if (ctrl.signal.aborted) return;
        setError(e instanceof Error ? e.message : "Failed to load the city");
      });
    return () => ctrl.abort();
  }, []);

  // Play sweeps the decade in ~14 seconds, then stops at year 10.
  useEffect(() => {
    if (!playing) return;
    let last = performance.now();
    const step = (now: number) => {
      const dt = (now - last) / 1000;
      last = now;
      setYear((y) => {
        const next = y + dt * (10 / 14);
        if (next >= 10) {
          setPlaying(false);
          return 10;
        }
        return next;
      });
      raf.current = requestAnimationFrame(step);
    };
    raf.current = requestAnimationFrame(step);
    return () => {
      if (raf.current !== null) cancelAnimationFrame(raf.current);
    };
  }, [playing]);

  const constants = useMemo(
    () => (scene ? cityConstants(scene.od) : null),
    [scene],
  );

  const state = useMemo(
    () => (constants ? predict(year, scenario, constants) : null),
    [constants, scenario, year],
  );
  const reference = useMemo(
    () => (constants ? predict(year, BASELINE_SCENARIO, constants) : null),
    [constants, year],
  );

  return (
    <section className="studio card" data-tour="map">
      <header className="studio-head">
        <div>
          <h2>Meridia — 3D digital twin</h2>
          <p className="studio-sub">
            {scene
              ? `${fmt(scene.sources.model.counts.buildings)} buildings · ${fmt(
                  scene.geometry.manifest.counts.roads,
                )} street links · ${fmt(
                  scene.geometry.manifest.counts.od_pairs,
                )} origin–destination pairs`
              : "Loading the prebuilt city model…"}
          </p>
        </div>
        <label className="switch">
          <input
            type="checkbox"
            checked={showFlows}
            onChange={(e) => setShowFlows(e.target.checked)}
          />
          Commute flows
        </label>
      </header>

      <div className="scenario-row" role="group" aria-label="Scenario">
        {SCENARIOS.map((s) => (
          <button
            key={s.id}
            type="button"
            className={`scenario-btn${scenario.id === s.id ? " active" : ""}`}
            onClick={() => setScenario(s)}
          >
            <span className="scenario-label">{s.label}</span>
            <span className="scenario-blurb">{s.blurb}</span>
          </button>
        ))}
      </div>

      <div className="scene-frame">
        {error ? (
          <SceneMessage label={`City unavailable — ${error}`} />
        ) : !scene || !state ? (
          <SceneMessage label="Loading Meridia…" />
        ) : (
          <>
            <CityCanvas
              scene={scene}
              year={year}
              state={state}
              scenario={scenario}
              showFlows={showFlows}
            />
            <div className="scene-badge">
              <strong>{yearLabel(year)}</strong>
              <span>{scenario.label}</span>
            </div>
            <div className="scene-key" aria-hidden>
              <span>
                <i className="sw" style={{ background: "#e29e42" }} /> under
                construction
              </span>
              <span>
                <i className="sw" style={{ background: "#42844f" }} /> new public
                realm
              </span>
              <span>
                <i className="sw" style={{ background: "#78aaff" }} /> charge
                cordon
              </span>
              <span className="scene-key-note">
                heights ×2.5 for legibility · drag to orbit
              </span>
            </div>
          </>
        )}
      </div>

      <div className="scrubber">
        <button
          type="button"
          className="play"
          onClick={() => {
            if (year >= 10) setYear(0);
            setPlaying((p) => !p);
          }}
          aria-label={playing ? "Pause" : "Play ten years"}
          disabled={!scene}
        >
          {playing ? "❚❚" : "▶"}
        </button>
        <input
          className="scrub-range"
          type="range"
          min={0}
          max={10}
          step={0.05}
          value={year}
          onChange={(e) => {
            setPlaying(false);
            setYear(Number(e.target.value));
          }}
          disabled={!scene}
          aria-label="Years after implementation"
        />
        <div className="scrub-ticks" aria-hidden>
          {YEAR_TICKS.map((t) => (
            <span key={t} className={year >= t ? "on" : ""}>
              {t === 0 ? "now" : `${t}y`}
            </span>
          ))}
        </div>
      </div>

      {state && reference && (
        <>
          <div className="outcome-strip">
            <div className="outcome">
              <span className="o-label">Cars into the centre</span>
              <span className="o-value">
                {fmt(state.carTripsIntoCbd)}
                <em>/day</em>
              </span>
              <Delta
                pct={deltaPct(state.carTripsIntoCbd, reference.carTripsIntoCbd)}
                goodWhenDown
              />
            </div>
            <div className="outcome">
              <span className="o-label">Traffic CO₂</span>
              <span className="o-value">
                {fmt(state.co2TonnesPerDay, 1)}
                <em>t/day</em>
              </span>
              <Delta
                pct={deltaPct(state.co2TonnesPerDay, reference.co2TonnesPerDay)}
                goodWhenDown
              />
            </div>
            <div className="outcome">
              <span className="o-label">Public transport</span>
              <span className="o-value">
                {fmt(state.transitTrips)}
                <em>trips/day</em>
              </span>
              <Delta
                pct={deltaPct(state.transitTrips, reference.transitTrips)}
                goodWhenDown={false}
              />
            </div>
            <div className="outcome">
              <span className="o-label">Street space for people</span>
              <span className="o-value">
                {fmt(state.publicRealm * 100)}
                <em>% of central kerbside</em>
              </span>
              <span className="delta flat">
                {state.publicRealm > 0
                  ? "reclaimed from traffic"
                  : "unchanged from today"}
              </span>
            </div>
            <div className="outcome">
              <span className="o-label">Public support</span>
              <span className="o-value">
                {fmt(state.support * 100)}
                <em>%</em>
              </span>
              <Delta
                pct={deltaPct(state.support, reference.support)}
                goodWhenDown={false}
              />
            </div>
          </div>

          <p className="studio-note">
            <span className="tag simulated">Simulated</span> Projected by the
            in-browser cordon demand-response model from the bundled
            origin–destination matrix and the same input assumptions the backend
            engine uses. Not an observation, and no language model produced any
            number here.
          </p>
        </>
      )}

      {scene && <SourcesNote sources={scene.sources} />}
    </section>
  );
}
