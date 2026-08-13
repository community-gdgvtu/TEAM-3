"use client";

/**
 * Flat, top-down plan of Meridia — the graceful degrade when WebGL is not
 * available (hardware acceleration off, old browser, headless preview). It
 * draws the *same* prebuilt geometry as the 3D `CityCanvas` — building
 * footprints, the river, the street grid, the charge cordon and the commute
 * flows — as an SVG plan, and responds to the same timeline state, so the demo
 * never collapses to a black box.
 *
 * No extrusion and no animation: footprints are coloured exactly like the 3D
 * view (construction amber, greening lots, congested streets), just seen from
 * straight above.
 */

import { useMemo } from "react";

import type {
  BuildingFeature,
  BuildingKind,
  RoadFeature,
  SceneData,
  ZoneProps,
} from "../../lib/city";
import type { CityState, Scenario } from "../../lib/cityModel";

// ---------------------------------------------------------------------------
// Palette (mirrors CityCanvas so the two views read identically)
// ---------------------------------------------------------------------------

type RGB = [number, number, number];

const GROUND: RGB = [15, 20, 33];
const WATER: RGB = [21, 48, 82];
const PARK: RGB = [42, 84, 55];
const NEW_PARK: RGB = [66, 132, 79];
const CONSTRUCTION: RGB = [226, 158, 66];
const CORDON: RGB = [120, 170, 255];

const KIND_COLOR: Record<BuildingKind, RGB> = {
  tower: [152, 168, 194],
  office: [133, 147, 173],
  podium: [98, 110, 134],
  mixed: [143, 133, 139],
  residential: [140, 125, 116],
  industrial: [104, 111, 124],
  lowrise: [88, 95, 111],
  park: PARK,
};

function css(c: RGB, alpha = 1): string {
  return `rgba(${c[0]}, ${c[1]}, ${c[2]}, ${alpha})`;
}

function mix(a: RGB, b: RGB, f: number): RGB {
  const t = Math.max(0, Math.min(1, f));
  return [
    Math.round(a[0] + t * (b[0] - a[0])),
    Math.round(a[1] + t * (b[1] - a[1])),
    Math.round(a[2] + t * (b[2] - a[2])),
  ];
}

function trafficColor(pressure: number): RGB {
  const stops: Array<[number, RGB]> = [
    [0.45, [72, 190, 150]],
    [0.85, [214, 196, 104]],
    [1.15, [232, 128, 78]],
    [1.45, [226, 76, 76]],
  ];
  const x = Math.max(stops[0][0], Math.min(stops[stops.length - 1][0], pressure));
  for (let i = 1; i < stops.length; i++) {
    const [t1, c1] = stops[i];
    if (x <= t1) {
      const [t0, c0] = stops[i - 1];
      const f = (x - t0) / (t1 - t0 || 1);
      return mix(c0, c1, f);
    }
  }
  return stops[stops.length - 1][1];
}

function idNoise(id: string): number {
  let h = 2166136261;
  for (let i = 0; i < id.length; i++) {
    h ^= id.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return ((h >>> 0) % 1000) / 1000;
}

function completion(f: BuildingFeature, year: number): number {
  const t0 = f.properties.t0;
  if (t0 <= 0) return 1;
  return Math.max(0, Math.min(1, (year - t0) / 1.2));
}

function greened(f: BuildingFeature, state: CityState): number {
  if (f.properties.g !== 1) return 0;
  const threshold = 0.15 + 0.7 * idNoise(String(f.id ?? f.properties.z));
  return Math.max(0, Math.min(1, (state.publicRealm - threshold) / 0.22));
}

/** Standing height in metres at this year/state — 0 means the lot is open. */
function buildingHeight(f: BuildingFeature, year: number, state: CityState): number {
  const p = f.properties;
  if (p.k === "park") return 0;
  const grown = p.h + p.dh * (year / 10) + p.td * state.tod;
  return grown * completion(f, year) * (1 - greened(f, state));
}

function buildingColor(f: BuildingFeature, year: number, state: CityState): RGB {
  const p = f.properties;
  if (p.k === "park") return PARK;
  const g = greened(f, state);
  if (g > 0) return mix(KIND_COLOR[p.k], NEW_PARK, g);
  const c = completion(f, year);
  if (c > 0 && c < 1) return mix(CONSTRUCTION, KIND_COLOR[p.k], c);
  const base = KIND_COLOR[p.k];
  const lift = Math.min(0.22, p.h / 900);
  return mix(base, [214, 206, 188], lift);
}

// ---------------------------------------------------------------------------
// Projection: lon/lat -> SVG, aspect-corrected for latitude
// ---------------------------------------------------------------------------

const PAD = 24;
const SPAN = 1000; // longest side of the drawable area, in SVG units

interface Projection {
  project: (lon: number, lat: number) => [number, number];
  width: number;
  height: number;
}

function makeProjection(scene: SceneData): Projection {
  let lon0 = Infinity;
  let lat0 = Infinity;
  let lon1 = -Infinity;
  let lat1 = -Infinity;
  const swallow = (lon: number, lat: number) => {
    if (lon < lon0) lon0 = lon;
    if (lon > lon1) lon1 = lon;
    if (lat < lat0) lat0 = lat;
    if (lat > lat1) lat1 = lat;
  };
  for (const f of scene.buildings.features) {
    for (const ring of f.geometry.coordinates) {
      for (const [lon, lat] of ring) swallow(lon, lat);
    }
  }
  for (const f of scene.water.features) {
    for (const ring of f.geometry.coordinates) {
      for (const [lon, lat] of ring) swallow(lon, lat);
    }
  }
  if (!Number.isFinite(lon0)) {
    // No geometry — degenerate but safe.
    lon0 = 0;
    lat0 = 0;
    lon1 = 1;
    lat1 = 1;
  }

  const midLat = (lat0 + lat1) / 2;
  const kx = Math.cos((midLat * Math.PI) / 180) || 1;
  const spanLon = (lon1 - lon0) * kx || 1;
  const spanLat = lat1 - lat0 || 1;
  const scale = SPAN / Math.max(spanLon, spanLat);
  const width = spanLon * scale + PAD * 2;
  const height = spanLat * scale + PAD * 2;

  const project = (lon: number, lat: number): [number, number] => [
    PAD + (lon - lon0) * kx * scale,
    PAD + (lat1 - lat) * scale, // flip: north is up
  ];
  return { project, width, height };
}

function ringToPoints(
  ring: number[][],
  project: (lon: number, lat: number) => [number, number],
): string {
  return ring
    .map(([lon, lat]) => {
      const [x, y] = project(lon, lat);
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function CityFallback2D({
  scene,
  year,
  state,
  showFlows,
}: {
  scene: SceneData;
  year: number;
  state: CityState;
  scenario: Scenario;
  showFlows: boolean;
}) {
  const { project, width, height } = useMemo(
    () => makeProjection(scene),
    [scene],
  );

  // Static geometry — projected once, recoloured on scrub.
  const waterPolys = useMemo(
    () =>
      scene.water.features.flatMap((f) =>
        f.geometry.coordinates.map((ring) => ringToPoints(ring, project)),
      ),
    [scene, project],
  );

  const roadPaths = useMemo(
    () =>
      (scene.geometry.roads.features as RoadFeature[]).map((f) => {
        const pts = (f.geometry.coordinates as [number, number][])
          .map(([lon, lat]) => {
            const [x, y] = project(lon, lat);
            return `${x.toFixed(1)},${y.toFixed(1)}`;
          })
          .join(" ");
        const inCordon = f.properties.crosses_cordon || f.properties.interior_cbd;
        const arterial = f.properties.road_class === "arterial";
        return { pts, inCordon, arterial, id: f.properties.link_id };
      }),
    [scene, project],
  );

  const cordonPoints = useMemo(() => {
    const rings = scene.geometry.cbd.geometry.coordinates as number[][][];
    return rings.map((ring) => ringToPoints(ring, project));
  }, [scene, project]);

  // Buildings: footprint projected once; fill recomputed for the current year.
  const buildingGeom = useMemo(
    () =>
      (scene.buildings.features as BuildingFeature[]).map((f, i) => ({
        f,
        key: String(f.id ?? i),
        points: ringToPoints(f.geometry.coordinates[0], project),
      })),
    [scene, project],
  );

  // Commute flows: home-zone centroid -> city centre, weighted by trips.
  const flows = useMemo(() => {
    if (!showFlows) return [];
    const zones = scene.geometry.zones.features;
    const centroid = new Map<string, [number, number]>();
    let cLon = 0;
    let cLat = 0;
    let cbdCount = 0;
    for (const z of zones) {
      const p = z.properties as ZoneProps;
      centroid.set(p.zone_id, [p.centroid_lon, p.centroid_lat]);
      if (p.is_cbd) {
        cLon += p.centroid_lon;
        cLat += p.centroid_lat;
        cbdCount += 1;
      }
    }
    if (cbdCount === 0) return [];
    const centre: [number, number] = [cLon / cbdCount, cLat / cbdCount];
    const byOrigin = new Map<string, number>();
    for (const pair of scene.od.pairs) {
      if (!pair.dest_is_cbd) continue;
      byOrigin.set(
        pair.origin,
        (byOrigin.get(pair.origin) ?? 0) + pair.daily_person_trips,
      );
    }
    const to = project(centre[0], centre[1]);
    const maxTrips = Math.max(1, ...byOrigin.values());
    return [...byOrigin.entries()].map(([zid, trips]) => {
      const home = centroid.get(zid) ?? centre;
      const from = project(home[0], home[1]);
      return {
        zid,
        x1: from[0],
        y1: from[1],
        x2: to[0],
        y2: to[1],
        w: Math.max(0.6, (trips / maxTrips) * 3.2),
      };
    });
  }, [scene, project, showFlows]);

  // Transit share pulls the flow colour amber -> blue, matching the 3D arcs.
  const flowColor = mix([226, 168, 92], CORDON, Math.min(1, state.tod));

  return (
    <svg
      className="scene-fallback-svg"
      viewBox={`0 0 ${width.toFixed(0)} ${height.toFixed(0)}`}
      preserveAspectRatio="xMidYMid meet"
      role="img"
      aria-label="Top-down plan of Meridia"
      style={{ position: "absolute", inset: 0, width: "100%", height: "100%" }}
    >
      <rect x={0} y={0} width={width} height={height} fill={css(GROUND)} />

      {waterPolys.map((pts, i) => (
        <polygon key={`w${i}`} points={pts} fill={css(WATER, 0.9)} />
      ))}

      {roadPaths.map((r, i) => (
        <polyline
          key={r.id ?? `r${i}`}
          points={r.pts}
          fill="none"
          stroke={
            r.inCordon
              ? css(trafficColor(state.congestion), 0.85)
              : "rgba(58, 68, 90, 0.8)"
          }
          strokeWidth={r.arterial ? 2.4 : 1.3}
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      ))}

      {buildingGeom.map(({ f, key, points }) => {
        const h = buildingHeight(f, year, state);
        const isPark = f.properties.k === "park";
        // A touch of opacity by height so the core still reads as the core.
        const opacity = isPark ? 0.55 : Math.min(1, 0.62 + h / 260);
        return (
          <polygon
            key={key}
            points={points}
            fill={css(buildingColor(f, year, state), opacity)}
          />
        );
      })}

      {showFlows &&
        flows.map((fl) => (
          <line
            key={`f${fl.zid}`}
            x1={fl.x1}
            y1={fl.y1}
            x2={fl.x2}
            y2={fl.y2}
            stroke={css(flowColor, 0.4)}
            strokeWidth={fl.w}
            strokeLinecap="round"
          />
        ))}

      {cordonPoints.map((pts, i) => (
        <polygon
          key={`c${i}`}
          points={pts}
          fill="none"
          stroke={css(CORDON, 0.85)}
          strokeWidth={2.4}
          strokeDasharray="6 4"
        />
      ))}
    </svg>
  );
}
