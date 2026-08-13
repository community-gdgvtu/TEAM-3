"use client";

/**
 * The 3D city. deck.gl renders the prebuilt Meridia model — ~1k building
 * footprints with real heights, the river, the street grid, live traffic trails
 * and the origin–destination commute flows — with no basemap and no tile
 * server, so it works offline.
 *
 * Everything the timeline changes is computed in `lib/cityModel.ts` and applied
 * here as accessors, so dragging the scrubber morphs the city at frame rate:
 *
 *   buildings   rise out of the pipeline, and grow taller where transit
 *               investment unlocks development
 *   kerbside    low-rise central lots convert to plazas and pocket parks as
 *               pedestrianisation is delivered
 *   streets     recolour from congested red toward free-flowing green, and the
 *               traffic trails thin out and speed up
 *   OD arcs     shift from car-amber to transit-blue as the mode split changes
 *
 * Geometry provenance: the building layer follows the LOD1 shape of a 3DCityDB
 * export (footprint polygon + height attribute) — see `public/city/sources.json`.
 */

import { useEffect, useMemo, useRef, useState } from "react";
import DeckGL from "@deck.gl/react";
import {
  AmbientLight,
  DirectionalLight,
  LightingEffect,
  MapView,
} from "@deck.gl/core";
import type { Color, PickingInfo } from "@deck.gl/core";
import { PathLayer, PolygonLayer } from "@deck.gl/layers";
import { TripsLayer } from "@deck.gl/geo-layers";

import type {
  BuildingFeature,
  BuildingKind,
  RoadFeature,
  SceneData,
  ZoneFeature,
} from "../../lib/city";
import type { CityState, Scenario } from "../../lib/cityModel";

// ---------------------------------------------------------------------------
// Palette
// ---------------------------------------------------------------------------

const GROUND: Color = [15, 20, 33];
const ZONE_FILL: Color = [24, 31, 48];
const WATER: Color = [21, 48, 82];
const PARK: Color = [42, 84, 55];
const NEW_PARK: Color = [66, 132, 79];
const CONSTRUCTION: Color = [226, 158, 66];
const CORDON: Color = [120, 170, 255];

/** Car share of trips into the centre today — the reference for arc colour. */
const CAR_SHARE_TODAY = 0.62;

const KIND_COLOR: Record<BuildingKind, Color> = {
  tower: [152, 168, 194],
  office: [133, 147, 173],
  podium: [98, 110, 134],
  mixed: [143, 133, 139],
  residential: [140, 125, 116],
  industrial: [104, 111, 124],
  lowrise: [88, 95, 111],
  park: PARK,
};

/** Free-flowing → busy → jammed, used for streets and traffic trails. */
function trafficColor(pressure: number): Color {
  const stops: Array<[number, Color]> = [
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
      return [
        Math.round(c0[0] + f * (c1[0] - c0[0])),
        Math.round(c0[1] + f * (c1[1] - c0[1])),
        Math.round(c0[2] + f * (c1[2] - c0[2])),
      ];
    }
  }
  return stops[stops.length - 1][1];
}

/** Same colour with a different alpha — keeps the tuple shape TypeScript wants. */
function rgba(c: Color, alpha: number): Color {
  return [c[0], c[1], c[2], alpha];
}

function mix(a: Color, b: Color, f: number): Color {
  const t = Math.max(0, Math.min(1, f));
  return [
    Math.round(a[0] + t * (b[0] - a[0])),
    Math.round(a[1] + t * (b[1] - a[1])),
    Math.round(a[2] + t * (b[2] - a[2])),
  ];
}

/** Stable 0–1 hash from a feature id, so per-building staggering is repeatable. */
function idNoise(id: string): number {
  let h = 2166136261;
  for (let i = 0; i < id.length; i++) {
    h ^= id.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return ((h >>> 0) % 1000) / 1000;
}

// ---------------------------------------------------------------------------
// Per-building time response
// ---------------------------------------------------------------------------

/** How far along its construction a pipeline building is at `year` (0–1). */
function completion(f: BuildingFeature, year: number): number {
  const t0 = f.properties.t0;
  if (t0 <= 0) return 1;
  return Math.max(0, Math.min(1, (year - t0) / 1.2));
}

/** How far this lot has been converted to public realm at this city state. */
function greened(f: BuildingFeature, state: CityState): number {
  if (f.properties.g !== 1) return 0;
  // Stagger conversions across lots so the centre greens block by block
  // rather than all at once.
  const threshold = 0.15 + 0.7 * idNoise(String(f.id ?? f.properties.z));
  return Math.max(0, Math.min(1, (state.publicRealm - threshold) / 0.22));
}

function buildingHeight(
  f: BuildingFeature,
  year: number,
  state: CityState,
): number {
  const p = f.properties;
  if (p.k === "park") return 0;
  const grown = p.h + p.dh * (year / 10) + p.td * state.tod;
  return grown * completion(f, year) * (1 - greened(f, state));
}

function buildingColor(
  f: BuildingFeature,
  year: number,
  state: CityState,
): Color {
  const p = f.properties;
  if (p.k === "park") return PARK;

  const g = greened(f, state);
  if (g > 0) return mix(KIND_COLOR[p.k], NEW_PARK, g);

  const c = completion(f, year);
  if (c > 0 && c < 1) return mix(CONSTRUCTION, KIND_COLOR[p.k], c);

  // A touch of warmth on the tall stuff so the core reads as the core.
  const base = KIND_COLOR[p.k];
  const lift = Math.min(0.22, p.h / 900);
  return mix(base, [214, 206, 188], lift);
}

// ---------------------------------------------------------------------------
// Commute flows
// ---------------------------------------------------------------------------

/** One home zone's total daily commute into the cordon, as a raised arc. */
interface Flow {
  path: [number, number, number][];
  trips: number;
}

const ARC_SEGMENTS = 26;
/** Apex of a flow arc as a fraction of its ground length. */
const ARC_RISE = 0.2;

/**
 * A parabolic 3D path from an origin zone to the city centre.
 *
 * Drawn as an explicit path rather than with ArcLayer: the height then lands in
 * the same metre-based world space as the buildings, so an arc always clears the
 * skyline instead of disappearing into it.
 */
function arcPath(
  from: [number, number],
  to: [number, number],
): [number, number, number][] {
  const midLat = ((from[1] + to[1]) / 2) * (Math.PI / 180);
  const dx = (to[0] - from[0]) * 111320 * Math.cos(midLat);
  const dy = (to[1] - from[1]) * 110540;
  const apex = Math.hypot(dx, dy) * ARC_RISE;
  const path: [number, number, number][] = [];
  for (let i = 0; i <= ARC_SEGMENTS; i++) {
    const t = i / ARC_SEGMENTS;
    path.push([
      from[0] + (to[0] - from[0]) * t,
      from[1] + (to[1] - from[1]) * t,
      apex * 4 * t * (1 - t),
    ]);
  }
  return path;
}

// ---------------------------------------------------------------------------
// Traffic trails
// ---------------------------------------------------------------------------

interface Trip {
  path: [number, number][];
  timestamps: [number, number];
  color: Color;
}

const LOOP = 1000;

/** Vertical exaggeration applied to real building heights, for legibility. */
export const HEIGHT_EXAGGERATION = 2.5;

/**
 * Turn the road network into animated vehicle trails. Trail *count* tracks how
 * much traffic the model says is on each link and trail *speed* tracks how
 * congested it is, so the same drag that empties the cordon also visibly speeds
 * the remaining traffic up.
 */
function buildTrips(
  roads: RoadFeature[],
  state: CityState,
  scenario: Scenario,
  rand: (i: number) => number,
): Trip[] {
  const trips: Trip[] = [];
  // Inside the cordon traffic follows the model; outside it barely moves.
  const cordonFactor = Math.max(0.05, state.congestion);
  const cityFactor = 0.85 + 0.15 * state.congestion;

  roads.forEach((r, i) => {
    const p = r.properties;
    const inCordon = p.crosses_cordon || p.interior_cbd;
    const factor = inCordon ? cordonFactor : cityFactor;
    // Pedestrianised interior streets lose through-traffic entirely.
    const closed = p.interior_cbd ? 1 - scenario.pedestrianise * 0.9 : 1;
    const base = p.road_class === "arterial" ? 4 : 2;
    const n = Math.round(base * factor * closed);
    if (n <= 0) return;

    const coords = r.geometry.coordinates as [number, number][];
    const pressure = inCordon ? state.congestion : cityFactor;
    const color = trafficColor(pressure);
    // Congested links take longer to traverse — the trails visibly crawl.
    const duration = LOOP * 0.16 * (0.55 + 0.75 * Math.min(1.5, pressure));

    for (let k = 0; k < n; k++) {
      const forward = (i + k) % 2 === 0;
      const path = forward ? coords : [...coords].reverse();
      const start =
        ((k / n + rand(i * 31 + k)) % 1) * Math.max(1, LOOP - duration);
      trips.push({
        path,
        timestamps: [start, start + duration],
        color,
      });
    }
  });
  return trips;
}

/** Deterministic jitter so trails don't march in lockstep. */
function jitter(seed: number): number {
  const x = Math.sin(seed * 12.9898) * 43758.5453;
  return x - Math.floor(x);
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export interface CityCanvasProps {
  scene: SceneData;
  year: number;
  state: CityState;
  scenario: Scenario;
  /** Draw the origin–destination commute arcs into the centre. */
  showFlows: boolean;
}

/**
 * Hoisted out of render on purpose: a fresh MapView / light instance on every
 * frame makes deck.gl invalidate its viewport and re-tessellate every layer,
 * which pegs the main thread once the traffic trails start animating.
 */
const MAP_VIEW = new MapView({ repeat: false });
/**
 * Scroll-zoom is off on purpose: the canvas sits inside a scrolling page, and a
 * map that swallows the wheel makes the page feel broken. Drag to orbit, drag
 * with shift to pan, double-click to zoom in.
 */
const CONTROLLER = {
  dragRotate: true,
  dragPan: true,
  scrollZoom: false,
  doubleClickZoom: true,
  touchZoom: true,
  keyboard: true,
};

const ambientLight = new AmbientLight({ color: [255, 255, 255], intensity: 1.1 });
const sunLight = new DirectionalLight({
  color: [255, 240, 220],
  intensity: 2.1,
  direction: [-1.2, -2.6, -1.6],
  _shadow: true,
});
const fillLight = new DirectionalLight({
  color: [150, 180, 255],
  intensity: 0.85,
  direction: [1.4, 1.0, -0.9],
});

export default function CityCanvas({
  scene,
  year,
  state,
  scenario,
  showFlows,
}: CityCanvasProps) {
  const { geometry, buildings, water, od } = scene;
  const { manifest } = geometry;
  const [time, setTime] = useState(0);
  const raf = useRef<number | null>(null);

  const effects = useMemo(() => {
    const effect = new LightingEffect({ ambientLight, sunLight, fillLight });
    effect.shadowColor = [0, 0, 0, 0.38];
    return [effect];
  }, []);

  // Animate the traffic trails at ~30fps — smooth enough for headlight trails,
  // and half the React re-renders of a raw 60fps loop.
  useEffect(() => {
    let mounted = true;
    let last = 0;
    const step = (now: number) => {
      if (!mounted) return;
      if (now - last > 33) {
        last = now;
        setTime((now / 26) % LOOP);
      }
      raf.current = requestAnimationFrame(step);
    };
    raf.current = requestAnimationFrame(step);
    return () => {
      mounted = false;
      if (raf.current !== null) cancelAnimationFrame(raf.current);
    };
  }, []);

  // The ground plate: the city footprint plus a generous apron.
  const groundPolygon = useMemo(() => {
    const { rows, cols, cell_km } = manifest.grid;
    const dLat = (cell_km * rows) / 111.32 / 2 + 0.012;
    const dLon =
      (cell_km * cols) / (111.32 * Math.cos((manifest.center.lat * Math.PI) / 180)) / 2 +
      0.012;
    const { lat, lon } = manifest.center;
    return [
      [lon - dLon, lat - dLat],
      [lon + dLon, lat - dLat],
      [lon + dLon, lat + dLat],
      [lon - dLon, lat + dLat],
    ];
  }, [manifest]);

  /**
   * The commute flows the model actually reads, aggregated one arc per home
   * zone: total daily trips from that zone into the cordon, drawn to the city
   * centre. Plotting raw OD *pairs* instead would just draw the highest-volume
   * ones, and a gravity matrix puts those between adjacent zones — dozens of
   * tiny hops buried in the skyline rather than the commute pattern.
   */
  const flows = useMemo(() => {
    const centroids = new Map<string, [number, number]>();
    let cbdLon = 0;
    let cbdLat = 0;
    let cbdCount = 0;
    for (const f of geometry.zones.features as ZoneFeature[]) {
      const p = f.properties;
      centroids.set(p.zone_id, [p.centroid_lon, p.centroid_lat]);
      if (p.is_cbd) {
        cbdLon += p.centroid_lon;
        cbdLat += p.centroid_lat;
        cbdCount += 1;
      }
    }
    if (cbdCount === 0) return [];
    const centre: [number, number] = [cbdLon / cbdCount, cbdLat / cbdCount];

    const byOrigin = new Map<string, number>();
    for (const p of od.pairs) {
      if (!p.dest_is_cbd) continue;
      byOrigin.set(
        p.origin,
        (byOrigin.get(p.origin) ?? 0) + p.daily_person_trips,
      );
    }

    const out: Flow[] = [];
    for (const [zone, trips] of byOrigin) {
      const from = centroids.get(zone);
      if (!from || trips <= 200) continue;
      out.push({ path: arcPath(from, centre), trips });
    }
    return out;
  }, [od, geometry]);

  const trips = useMemo(
    () =>
      buildTrips(
        geometry.roads.features as RoadFeature[],
        state,
        scenario,
        jitter,
      ),
    [geometry, state, scenario],
  );

  const baseLayers = useMemo(() => {
    // Arc colour tracks the mode split: amber while the flow is car-dominated,
    // blue as the charge pushes it onto public transport and walking. Measured
    // against today's car share rather than congestion, which pedestrianisation
    // holds flat by shrinking road capacity as fast as it removes cars.
    const shiftToTransit = 1 - state.carShareIntoCbd / CAR_SHARE_TODAY;
    const arcCar: Color = [235, 170, 84];
    const arcTransit: Color = [96, 168, 255];
    const flowColor = mix(arcCar, arcTransit, shiftToTransit);

    return [
      new PolygonLayer({
        id: "ground",
        data: [{ polygon: groundPolygon }],
        getPolygon: (d: { polygon: number[][] }) => d.polygon,
        getFillColor: GROUND,
        stroked: false,
        extruded: false,
      }),
      new PolygonLayer({
        id: "zones",
        data: geometry.zones.features as ZoneFeature[],
        getPolygon: (f: ZoneFeature) => f.geometry.coordinates as never,
        getFillColor: (f: ZoneFeature) =>
          f.properties.is_cbd ? ([30, 40, 62] as Color) : ZONE_FILL,
        getLineColor: [10, 14, 24, 160],
        stroked: true,
        filled: true,
        extruded: false,
        lineWidthMinPixels: 1,
      }),
      new PolygonLayer({
        id: "water",
        data: water.features,
        getPolygon: (f: { geometry: { coordinates: number[][][] } }) =>
          f.geometry.coordinates as never,
        getFillColor: WATER,
        stroked: false,
        extruded: false,
      }),
      new PathLayer({
        id: "streets",
        data: geometry.roads.features as RoadFeature[],
        getPath: (f: RoadFeature) => f.geometry.coordinates as [number, number][],
        getColor: (f: RoadFeature) => {
          const p = f.properties;
          const inCordon = p.crosses_cordon || p.interior_cbd;
          if (!inCordon) return [58, 68, 90] as Color;
          return rgba(trafficColor(state.congestion), 210);
        },
        getWidth: (f: RoadFeature) =>
          f.properties.road_class === "arterial" ? 14 : 8,
        widthUnits: "meters",
        widthMinPixels: 1,
        capRounded: true,
        jointRounded: true,
        updateTriggers: { getColor: [state.congestion] },
      }),
      new PolygonLayer({
        id: "buildings",
        data: buildings.features as BuildingFeature[],
        getPolygon: (f: BuildingFeature) => f.geometry.coordinates as never,
        extruded: true,
        filled: true,
        stroked: false,
        pickable: true,
        wireframe: false,
        getElevation: (f: BuildingFeature) => buildingHeight(f, year, state),
        // Heights are real metres, scaled up for legibility — at this zoom a
        // true-to-scale 100 m tower is barely ten pixels tall. Stated in the
        // on-canvas key so nobody reads the skyline as a measurement.
        elevationScale: HEIGHT_EXAGGERATION,
        getFillColor: (f: BuildingFeature) => buildingColor(f, year, state),
        material: {
          ambient: 0.42,
          diffuse: 0.68,
          shininess: 24,
          specularColor: [70, 90, 120],
        },
        updateTriggers: {
          getElevation: [year, state.tod, state.publicRealm],
          getFillColor: [year, state.tod, state.publicRealm],
        },
      }),
      new PolygonLayer({
        id: "cordon",
        data: [geometry.cbd],
        getPolygon: (f: { geometry: { coordinates: number[][][] } }) =>
          f.geometry.coordinates as never,
        stroked: true,
        filled: false,
        extruded: false,
        getLineColor: rgba(CORDON, 220),
        getLineWidth: 26,
        widthUnits: "meters",
        lineWidthMinPixels: 2,
      }),
      showFlows &&
        new PathLayer({
          id: "od-flows",
          data: flows,
          getPath: (d: Flow) => d.path,
          getColor: rgba(flowColor, 105),
          getWidth: (d: Flow) => Math.max(1.1, Math.sqrt(d.trips) / 9),
          widthUnits: "pixels",
          widthMinPixels: 1,
          capRounded: true,
          jointRounded: true,
          updateTriggers: { getColor: [flowColor] },
        }),
    ].filter(Boolean);
  }, [geometry, buildings, water, groundPolygon, year, state, flows, showFlows]);

  // The traffic trails are the only thing that changes every frame, so they are
  // rebuilt outside the memo above — otherwise deck.gl would be handed a fresh
  // 1k-polygon building layer sixty times a second.
  const layers = useMemo(
    () => [
      ...baseLayers,
      new TripsLayer({
        id: "traffic",
        data: trips,
        getPath: (d: Trip) => d.path,
        getTimestamps: (d: Trip) => d.timestamps,
        getColor: (d: Trip) => d.color,
        currentTime: time,
        trailLength: 55,
        fadeTrail: true,
        widthMinPixels: 2.8,
        capRounded: true,
        jointRounded: true,
        opacity: 0.95,
      }),
    ],
    [baseLayers, trips, time],
  );

  return (
    <DeckGL
      views={MAP_VIEW}
      initialViewState={{
        longitude: manifest.center.lon,
        latitude: manifest.center.lat - 0.011,
        zoom: 13.35,
        pitch: 54,
        bearing: -20,
        maxPitch: 75,
        minZoom: 11,
        maxZoom: 17,
      }}
      controller={CONTROLLER}
      effects={effects}
      layers={layers as never}
      getTooltip={getTooltip}
      style={{ position: "absolute", inset: "0" }}
    />
  );
}

function getTooltip(info: PickingInfo): string | null {
  const f = info.object as BuildingFeature | undefined;
  const p = f?.properties;
  if (!p || p.k === "park") return null;
  const bits = [
    `${p.k} · zone ${p.z}`,
    `${p.h.toFixed(0)} m today`,
    p.dh > 0 ? `+${p.dh.toFixed(0)} m by year 10 (pipeline)` : "",
    p.td > 0 ? `+${p.td.toFixed(0)} m if transit is funded` : "",
    p.t0 > 0 ? `breaks ground in year ${p.t0.toFixed(1)}` : "",
    p.g === 1 ? "can become public realm" : "",
  ].filter(Boolean);
  return bits.join("\n");
}
