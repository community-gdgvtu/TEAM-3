/**
 * City geometry loader for the 3D map (SPEC §17/§27).
 *
 * The synthetic Meridia world state (zones / roads / CBD cordon) is bundled as
 * static GeoJSON under `public/city/` so the map renders even before the backend
 * exposes a geometry endpoint. If the backend later serves `/city/*.geojson`
 * (same filenames), point `NEXT_PUBLIC_CITY_BASE_URL` at it and the loader will
 * prefer that. The geometry is world *input*, tagged Synthetic — it is not a
 * simulation result and no LLM produced it (SPEC §34).
 */

import type {
  Feature,
  FeatureCollection,
  LineString,
  Polygon,
} from "geojson";

/** Where the GeoJSON assets live. Defaults to the bundled copies in `public/`. */
export const CITY_BASE_URL =
  process.env.NEXT_PUBLIC_CITY_BASE_URL ?? "/city";

export interface ZoneProps {
  zone_id: string;
  row: number;
  col: number;
  category: string;
  land_use: string;
  is_cbd: boolean;
  area_km2: number;
  population: number;
  households: number;
  jobs: number;
  centroid_lon: number;
  centroid_lat: number;
}

export interface RoadProps {
  link_id: string;
  from_zone: string;
  to_zone: string;
  road_class: string;
  lanes: number;
  length_km: number;
  capacity_veh_per_hr: number;
  free_flow_speed_kmh: number;
  crosses_cordon: boolean;
  interior_cbd: boolean;
}

export interface CbdProps {
  name: string;
  zone_ids: string[];
  description: string;
}

export type ZoneFeature = Feature<Polygon, ZoneProps>;
export type RoadFeature = Feature<LineString, RoadProps>;
export type CbdFeature = Feature<Polygon, CbdProps>;

export interface CityManifest {
  title: string;
  provenance: string;
  center: { lat: number; lon: number };
  grid: { rows: number; cols: number; cell_km: number };
  counts: Record<string, number>;
  totals: Record<string, number>;
}

export interface CityGeometry {
  zones: FeatureCollection<Polygon, ZoneProps>;
  roads: FeatureCollection<LineString, RoadProps>;
  cbd: CbdFeature;
  manifest: CityManifest;
}

async function fetchJson<T>(path: string, signal?: AbortSignal): Promise<T> {
  const res = await fetch(`${CITY_BASE_URL}/${path}`, {
    signal,
    cache: "force-cache",
  });
  if (!res.ok) {
    throw new Error(`Failed to load ${path}: HTTP ${res.status}`);
  }
  return (await res.json()) as T;
}

/** Load all city geometry needed by the map in parallel. Throws on failure. */
export async function loadCityGeometry(
  signal?: AbortSignal,
): Promise<CityGeometry> {
  const [zones, roads, cbd, manifest] = await Promise.all([
    fetchJson<FeatureCollection<Polygon, ZoneProps>>("zones.geojson", signal),
    fetchJson<FeatureCollection<LineString, RoadProps>>("roads.geojson", signal),
    fetchJson<CbdFeature>("cbd_polygon.geojson", signal),
    fetchJson<CityManifest>("manifest.json", signal),
  ]);
  return { zones, roads, cbd, manifest };
}

// ---------------------------------------------------------------------------
// Origin–destination trip matrix (synthetic world input, SPEC §34)
// ---------------------------------------------------------------------------

export interface OdPair {
  origin: string;
  destination: string;
  daily_person_trips: number;
  distance_km: number;
  dest_is_cbd: boolean;
}

export interface OdMatrix {
  name: string;
  units: string;
  model: string;
  interpretation: string;
  pairs: OdPair[];
}

/**
 * Load the synthetic origin–destination commute matrix. Loaded lazily (~0.4 MB)
 * only when an overlay that needs real demand asks for it. This is world input,
 * not a simulation result.
 */
export async function loadOdMatrix(signal?: AbortSignal): Promise<OdMatrix> {
  return fetchJson<OdMatrix>("od_pairs.json", signal);
}

/** Sum daily inflow (trip attraction) per destination zone from the OD matrix. */
export function inflowByZone(od: OdMatrix): Map<string, number> {
  const m = new Map<string, number>();
  for (const p of od.pairs) {
    m.set(p.destination, (m.get(p.destination) ?? 0) + p.daily_person_trips);
  }
  return m;
}
