/**
 * Data-driven map overlay *layers* (SPEC §17/§27): traffic flow, transit demand,
 * and a support/opposition heatmap. Provenance/captions live in `overlayMeta.ts`
 * (pure); this module only builds deck.gl layers and is imported solely by the
 * SSR-disabled map component.
 *
 * Honesty (SPEC §34): transit is derived from the real synthetic OD matrix
 * (world input); traffic and support are illustrative placeholders until the
 * backend `/simulate` produces real per-link and behavioural numbers.
 */

import { GeoJsonLayer } from "@deck.gl/layers";
import { HeatmapLayer } from "@deck.gl/aggregation-layers";
import type { Layer } from "@deck.gl/core";

import type { CityGeometry, OdMatrix, RoadProps, ZoneProps } from "../../lib/city";
import { inflowByZone } from "../../lib/city";
import type { OverlayMode } from "./overlayMeta";

function clamp01(x: number): number {
  return Math.max(0, Math.min(1, x));
}

/** Diverging red(oppose)→grey→green(support) at t in [-1, 1]. */
function divergingRGBA(t: number): [number, number, number, number] {
  const oppose: [number, number, number] = [220, 84, 84];
  const neutral: [number, number, number] = [120, 130, 150];
  const support: [number, number, number] = [80, 200, 120];
  const x = Math.max(-1, Math.min(1, t));
  const mix = (
    a: [number, number, number],
    b: [number, number, number],
    f: number,
  ): [number, number, number] => [
    Math.round(a[0] + f * (b[0] - a[0])),
    Math.round(a[1] + f * (b[1] - a[1])),
    Math.round(a[2] + f * (b[2] - a[2])),
  ];
  const [r, g, b] = x < 0 ? mix(neutral, oppose, -x) : mix(neutral, support, x);
  return [r, g, b, 200];
}

/** Green(low)→amber→red(high) load ramp at t in [0, 1]. */
function loadRGBA(t: number): [number, number, number, number] {
  const x = clamp01(t);
  if (x < 0.5) {
    const f = x / 0.5;
    return [Math.round(80 + f * 166), Math.round(200 - f * 10), 90, 220];
  }
  const f = (x - 0.5) / 0.5;
  return [246, Math.round(190 - f * 130), Math.round(90 - f * 30), 230];
}

function trafficLayers(geometry: CityGeometry): Layer[] {
  let maxCap = 1;
  for (const r of geometry.roads.features) {
    maxCap = Math.max(maxCap, r.properties.capacity_veh_per_hr);
  }
  return [
    new GeoJsonLayer<RoadProps>({
      id: "overlay-traffic",
      data: geometry.roads,
      pickable: true,
      stroked: false,
      filled: false,
      getLineColor: (f) => {
        const p = f.properties as RoadProps;
        const idx = clamp01(
          (p.capacity_veh_per_hr / maxCap) * (p.crosses_cordon ? 1.15 : 1),
        );
        return loadRGBA(idx);
      },
      getLineWidth: (f) => {
        const p = f.properties as RoadProps;
        return (p.capacity_veh_per_hr / maxCap) * 5 + (p.crosses_cordon ? 2 : 0.8);
      },
      lineWidthUnits: "pixels",
      lineWidthMinPixels: 1.2,
    }),
  ];
}

function transitLayers(geometry: CityGeometry, od: OdMatrix | null): Layer[] {
  if (!od) return [];
  const inflow = inflowByZone(od);
  const points = geometry.zones.features.map((f) => ({
    position: [f.properties.centroid_lon, f.properties.centroid_lat] as [
      number,
      number,
    ],
    weight: inflow.get(f.properties.zone_id) ?? 0,
  }));
  return [
    new HeatmapLayer<{ position: [number, number]; weight: number }>({
      id: "overlay-transit",
      data: points,
      getPosition: (d) => d.position,
      getWeight: (d) => d.weight,
      radiusPixels: 55,
      intensity: 1,
      threshold: 0.03,
      aggregation: "SUM",
    }),
  ];
}

function supportLayers(geometry: CityGeometry): Layer[] {
  const { center } = geometry.manifest;
  let maxDist = 1e-9;
  const dists = geometry.zones.features.map((f) => {
    const d = Math.hypot(
      f.properties.centroid_lon - center.lon,
      f.properties.centroid_lat - center.lat,
    );
    maxDist = Math.max(maxDist, d);
    return d;
  });
  return [
    new GeoJsonLayer<ZoneProps>({
      id: "overlay-support",
      data: geometry.zones,
      pickable: true,
      stroked: true,
      filled: true,
      extruded: false,
      getLineColor: [12, 18, 33, 160],
      lineWidthMinPixels: 0.5,
      getFillColor: (f, { index }) => {
        const p = f.properties as ZoneProps;
        const norm = dists[index] / maxDist;
        let score = 1 - 2 * norm; // +1 centre → -1 edge (illustrative)
        if (p.is_cbd) score = 0.9;
        if (p.land_use === "industrial") score -= 0.25;
        return divergingRGBA(score);
      },
    }),
  ];
}

/** Build deck.gl layers for the selected overlay (empty for "none"). */
export function buildOverlayLayers(
  mode: OverlayMode,
  geometry: CityGeometry,
  od: OdMatrix | null,
): Layer[] {
  switch (mode) {
    case "traffic":
      return trafficLayers(geometry);
    case "transit":
      return transitLayers(geometry, od);
    case "support":
      return supportLayers(geometry);
    default:
      return [];
  }
}
