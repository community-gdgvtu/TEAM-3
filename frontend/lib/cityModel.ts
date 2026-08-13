/**
 * The reduced-form cordon demand-response model that the 10-year scrubber drives.
 *
 * Why this exists alongside the FastAPI engine: dragging a timeline has to feel
 * instant, so the *visual* city cannot wait on a network round-trip per frame.
 * This module is a deterministic, closed-form summary of the same mechanism the
 * backend runs step-wise — it takes the identical input assumptions
 * (`backend/app/baseline/params.py`) and the identical OD matrix, so the curves
 * agree in shape and at the endpoints. The full agent-based engine, the
 * uncertainty bands and the parliament all still live behind /simulate.
 *
 * Epistemic rule (SPEC §34): everything below is a mechanistic transform of
 * documented input assumptions. No LLM produces any number here, and nothing
 * here is presented as an observation — the UI tags it Simulated.
 *
 * Provenance of the mechanism (see `public/city/sources.json`):
 *   - travel demand shaped like ONS 2011 Census OD table WU03EW (home→work
 *     flows by mode), which `od_pairs.json` reproduces as a schema;
 *   - built form shaped like a 3DCityDB LOD1 export (footprint + height).
 */

import type { OdMatrix } from "./city";

// ---------------------------------------------------------------------------
// Input assumptions — mirrored from backend/app/baseline/params.py
// ---------------------------------------------------------------------------

export const ASSUMPTIONS = {
  /** Congested central speed, km/h. */
  carSpeedCbdKmh: 18.0,
  /** Parking search + walk from parking, minutes per one-way trip. */
  carOverheadMin: 6.0,
  /** Fuel + wear, currency units per km. */
  carCostPerKm: 0.25,
  /** Minutes of disutility per currency unit — converts money to time. */
  moneyToMinutes: 8.0,
  /** Average tailpipe CO₂ for a petrol car, kg per vehicle-km. */
  carCo2KgPerKm: 0.192,
  /** Average car occupancy for commuting — person-trips ÷ vehicle-trips. */
  carOccupancy: 1.2,
  /** Mode split of trips into the centre today. */
  modeSplit0: { car: 0.62, transit: 0.26, walk: 0.12 },
  /** Exogenous background demand growth, compounded per year (no policy). */
  demandGrowthPerYear: 0.015,
  /**
   * Elasticity of car trips to the generalised cost of the trip. Cordon
   * schemes cluster around −0.3 to −0.4; −0.35 is the midpoint.
   */
  costElasticity: -0.35,
  /** Behavioural adjustment time constant, years (≈84% of the response by 2y). */
  behaviourTauYears: 1.1,
  /** Where suppressed car trips go. Must sum to 1. */
  reallocation: { transit: 0.55, walk: 0.2, reroute: 0.15, forgone: 0.1 },
  /** Baseline transit capacity headroom, as a share of today's ridership. */
  transitHeadroom0: 0.06,
  /** Extra headroom by year 10 at full reinvestment. */
  transitHeadroomFromInvestment: 0.34,
} as const;

// ---------------------------------------------------------------------------
// Scenarios — the whole "simulator" the simple view exposes
// ---------------------------------------------------------------------------

export interface Scenario {
  id: string;
  label: string;
  blurb: string;
  /** Charge per vehicle entering the cordon, currency units. */
  charge: number;
  /** Share of charge revenue reinvested in public transport, 0–1. */
  reinvest: number;
  /** Share of central street space handed to people, 0–1. */
  pedestrianise: number;
}

export const SCENARIOS: Scenario[] = [
  {
    id: "baseline",
    label: "Do nothing",
    blurb:
      "No charge, no reallocation of street space. Demand drifts up with the background growth trend.",
    charge: 0,
    reinvest: 0,
    pedestrianise: 0,
  },
  {
    id: "charge",
    label: "Congestion charge",
    blurb:
      "Price every vehicle entering the central cordon and put the revenue into public transport.",
    charge: 5,
    reinvest: 0.8,
    pedestrianise: 0,
  },
  {
    id: "pedestrianise",
    label: "Charge + pedestrianise",
    blurb:
      "The charge, plus handing most central street space back to people — plazas, pocket parks, wider footways.",
    charge: 5,
    reinvest: 1,
    pedestrianise: 0.7,
  },
];

export const BASELINE_SCENARIO = SCENARIOS[0];

// ---------------------------------------------------------------------------
// City constants derived once from the bundled OD matrix
// ---------------------------------------------------------------------------

export interface CityConstants {
  /** Daily person-trips whose destination is inside the cordon. */
  tripsIntoCbd: number;
  /** Daily person-trips citywide. */
  tripsTotal: number;
  /** Trip-weighted mean distance of a trip into the cordon, km. */
  meanCbdDistanceKm: number;
  /** Trip-weighted mean distance of any trip, km. */
  meanDistanceKm: number;
}

/** Reduce the OD matrix to the four numbers the model needs. */
export function cityConstants(od: OdMatrix): CityConstants {
  let intoCbd = 0;
  let total = 0;
  let cbdKm = 0;
  let allKm = 0;
  for (const p of od.pairs) {
    total += p.daily_person_trips;
    allKm += p.daily_person_trips * p.distance_km;
    if (p.dest_is_cbd) {
      intoCbd += p.daily_person_trips;
      cbdKm += p.daily_person_trips * p.distance_km;
    }
  }
  return {
    tripsIntoCbd: intoCbd,
    tripsTotal: total,
    meanCbdDistanceKm: intoCbd > 0 ? cbdKm / intoCbd : 0,
    meanDistanceKm: total > 0 ? allKm / total : 0,
  };
}

// ---------------------------------------------------------------------------
// The model
// ---------------------------------------------------------------------------

export interface CityState {
  year: number;
  /** Daily car person-trips crossing into the cordon. */
  carTripsIntoCbd: number;
  /** Daily public-transport trips citywide. */
  transitTrips: number;
  /** Daily walk/cycle trips into the cordon. */
  walkTripsIntoCbd: number;
  /** Daily vehicle-km citywide. */
  vehicleKm: number;
  /** Tonnes of tailpipe CO₂ per day. */
  co2TonnesPerDay: number;
  /** Central traffic pressure indexed to today (1.0 = today's level). */
  congestion: number;
  /** Share of all trips into the centre still made by car, 0–1. */
  carShareIntoCbd: number;
  /** Share of central kerbside converted to public realm, 0–1. */
  publicRealm: number;
  /** Transit-oriented development progress, 0–1. */
  tod: number;
  /** Modelled public support for the policy, 0–1. */
  support: number;
}

const clamp = (x: number, lo: number, hi: number) =>
  Math.max(lo, Math.min(hi, x));

/** Behavioural response ramp: 0 at implementation, →1 over a couple of years. */
function behaviourRamp(year: number): number {
  return 1 - Math.exp(-Math.max(0, year) / ASSUMPTIONS.behaviourTauYears);
}

/** Generalised cost of one car trip into the centre, in minutes. */
function carGeneralisedCostMin(distanceKm: number): number {
  const a = ASSUMPTIONS;
  return (
    (distanceKm / a.carSpeedCbdKmh) * 60 +
    a.carOverheadMin +
    distanceKm * a.carCostPerKm * a.moneyToMinutes
  );
}

/**
 * Project the city to `year` (0–10) under `scenario`.
 *
 * Chain: background growth → generalised-cost shock → constant-elasticity
 * demand response → reallocation of suppressed trips subject to transit
 * capacity → downstream vehicle-km, CO₂, congestion → land-use response.
 */
export function predict(
  year: number,
  scenario: Scenario,
  c: CityConstants,
): CityState {
  const a = ASSUMPTIONS;
  const y = clamp(year, 0, 10);
  const growth = Math.pow(1 + a.demandGrowthPerYear, y);
  const ramp = behaviourRamp(y);

  // --- demand into the cordon under no intervention ------------------------
  const tripsIntoCbd = c.tripsIntoCbd * growth;
  const car0 = tripsIntoCbd * a.modeSplit0.car;
  const transit0 = c.tripsTotal * growth * a.modeSplit0.transit;
  const walk0 = tripsIntoCbd * a.modeSplit0.walk;

  // --- the cost shock ------------------------------------------------------
  // The charge is per vehicle, so it is shared over the car's occupants.
  const chargePerPerson = scenario.charge / a.carOccupancy;
  const gc0 = carGeneralisedCostMin(c.meanCbdDistanceKm);
  const dCost = (chargePerPerson * a.moneyToMinutes) / gc0;

  // Constant-elasticity demand curve in power form — the linear form would
  // over-shoot badly at a cost increase this large. Plus the direct capacity
  // effect of handing street space to people, which is independent of price.
  const priceEffect = Math.pow(1 + dCost, a.costElasticity) - 1;
  const spaceEffect = -0.22 * scenario.pedestrianise;
  const carChange = clamp((priceEffect + spaceEffect) * ramp, -0.85, 0.2);

  const carTripsIntoCbd = car0 * (1 + carChange);
  const suppressed = car0 - carTripsIntoCbd;

  // --- where the suppressed trips go --------------------------------------
  const r = a.reallocation;
  let toTransit = suppressed * r.transit;
  const toWalk = suppressed * r.walk;
  const rerouted = suppressed * r.reroute;

  // Transit can only absorb what it has room for. Reinvestment buys headroom,
  // ramping in over the horizon (vehicles ordered, services added).
  const headroom =
    transit0 *
    (a.transitHeadroom0 +
      a.transitHeadroomFromInvestment * scenario.reinvest * clamp(y / 8, 0, 1));
  const spillback = Math.max(0, toTransit - headroom);
  toTransit -= spillback;

  const carFinal = carTripsIntoCbd + spillback;
  const transitTrips = transit0 + toTransit;
  const walkTripsIntoCbd = walk0 + toWalk;

  // --- downstream volumes --------------------------------------------------
  // Citywide vehicle-km: trips that never entered the cordon are unaffected;
  // rerouted trips still drive, and take a ~1.35× detour around the cordon.
  const carVehicleTripsBase =
    (c.tripsTotal * growth * a.modeSplit0.car) / a.carOccupancy;
  const removedVehicleTrips = (car0 - carFinal) / a.carOccupancy;
  const reroutedVehicleTrips = rerouted / a.carOccupancy;
  const vehicleKm =
    (carVehicleTripsBase - removedVehicleTrips - reroutedVehicleTrips) *
      c.meanDistanceKm +
    reroutedVehicleTrips * c.meanCbdDistanceKm * 1.35;

  const co2TonnesPerDay = (vehicleKm * a.carCo2KgPerKm) / 1000;

  // Central traffic pressure, indexed so today = 1.0. Car volume is measured
  // against a road capacity that *shrinks* as street space is pedestrianised.
  const capacityFactor = 1 - 0.55 * scenario.pedestrianise;
  const congestion = clamp(
    (carFinal / (c.tripsIntoCbd * a.modeSplit0.car)) / capacityFactor,
    0,
    1.6,
  );

  // --- land-use response (slow) -------------------------------------------
  // Public realm has to be designed, consulted and built: nothing in year 1,
  // most of it delivered by year 6.
  const publicRealm =
    scenario.pedestrianise * clamp((y - 0.8) / 5, 0, 1);
  // Transit-oriented development needs the transit to exist first.
  const tod = scenario.reinvest * clamp((y - 2) / 6, 0, 1);

  // --- public support ------------------------------------------------------
  // Charges are unpopular on day one and recover as the benefits land — the
  // pattern every real cordon scheme has shown.
  const disruption = (scenario.charge > 0 ? 0.28 : 0) * Math.exp(-y / 1.6);
  const benefit =
    0.3 * (1 - congestion) + 0.25 * publicRealm + 0.15 * tod;
  const support = clamp(0.5 - disruption + benefit * ramp, 0.05, 0.95);

  return {
    year: y,
    carShareIntoCbd: tripsIntoCbd > 0 ? carFinal / tripsIntoCbd : 0,
    carTripsIntoCbd: carFinal,
    transitTrips,
    walkTripsIntoCbd,
    vehicleKm,
    co2TonnesPerDay,
    congestion,
    publicRealm,
    tod,
    support,
  };
}

/** Percentage change of `value` against the do-nothing world at the same year. */
export function deltaPct(value: number, reference: number): number | null {
  if (!Number.isFinite(reference) || reference === 0) return null;
  return ((value - reference) / reference) * 100;
}
