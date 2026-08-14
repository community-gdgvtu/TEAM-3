/**
 * Unit tests for the client-side reduced-form city model (lib/cityModel.ts) and
 * the OD aggregation helper (lib/city.ts inflowByZone).
 *
 * These are honesty-critical (SPEC §34): `predict` produces *every* number the
 * 10-year timeline scrubber paints on the 3D city and the simple-view dashboard,
 * and `deltaPct` renders the "% vs do-nothing" figures beside them. There is no
 * network round-trip in this path, so nothing but these functions guards those
 * numbers — a silent regression here corrupts what a judge reads while dragging
 * the timeline. The module is deterministic and closed-form, so we can pin the
 * arithmetic (cityConstants, deltaPct) exactly and pin `predict` against its
 * documented invariants and bounds. Zero-dependency runner: npm test.
 */

import { test } from "node:test";
import assert from "node:assert/strict";

import {
  ASSUMPTIONS,
  SCENARIOS,
  BASELINE_SCENARIO,
  cityConstants,
  predict,
  deltaPct,
  type Scenario,
  type CityConstants,
} from "../lib/cityModel.ts";
import { inflowByZone, type OdMatrix } from "../lib/city.ts";

// A tiny synthetic OD matrix with hand-checkable totals.
const OD: OdMatrix = {
  name: "test",
  units: "daily person-trips",
  model: "synthetic",
  interpretation: "test fixture",
  pairs: [
    { origin: "A", destination: "CBD", daily_person_trips: 1000, distance_km: 5, dest_is_cbd: true },
    { origin: "B", destination: "CBD", daily_person_trips: 500, distance_km: 10, dest_is_cbd: true },
    { origin: "C", destination: "D", daily_person_trips: 300, distance_km: 2, dest_is_cbd: false },
  ],
};

// Realistic constants used to exercise `predict` independently of the OD fixture.
const C: CityConstants = {
  tripsIntoCbd: 100_000,
  tripsTotal: 400_000,
  meanCbdDistanceKm: 6,
  meanDistanceKm: 8,
};

const CHARGE = SCENARIOS.find((s) => s.id === "charge") as Scenario;
const PED = SCENARIOS.find((s) => s.id === "pedestrianise") as Scenario;

// ---------------------------------------------------------------------------
// cityConstants — pure arithmetic over the OD matrix
// ---------------------------------------------------------------------------

test("cityConstants: sums trips and splits CBD from citywide", () => {
  const c = cityConstants(OD);
  assert.equal(c.tripsTotal, 1800);
  assert.equal(c.tripsIntoCbd, 1500);
});

test("cityConstants: trip-weighted mean distances", () => {
  const c = cityConstants(OD);
  // CBD: (1000*5 + 500*10) / 1500 = 10000/1500
  assert.equal(c.meanCbdDistanceKm, 10000 / 1500);
  // All: (10000 + 300*2) / 1800 = 10600/1800
  assert.equal(c.meanDistanceKm, 10600 / 1800);
});

test("cityConstants: empty matrix is all zeros, never NaN", () => {
  const c = cityConstants({ ...OD, pairs: [] });
  assert.equal(c.tripsTotal, 0);
  assert.equal(c.tripsIntoCbd, 0);
  assert.equal(c.meanCbdDistanceKm, 0);
  assert.equal(c.meanDistanceKm, 0);
});

// ---------------------------------------------------------------------------
// inflowByZone — trip attraction per destination
// ---------------------------------------------------------------------------

test("inflowByZone: aggregates daily inflow per destination zone", () => {
  const m = inflowByZone(OD);
  assert.equal(m.get("CBD"), 1500);
  assert.equal(m.get("D"), 300);
  assert.equal(m.size, 2);
});

test("inflowByZone: empty matrix yields an empty map", () => {
  assert.equal(inflowByZone({ ...OD, pairs: [] }).size, 0);
});

// ---------------------------------------------------------------------------
// deltaPct — the "% vs do-nothing" renderer
// ---------------------------------------------------------------------------

test("deltaPct: signed percentage change", () => {
  assert.equal(deltaPct(110, 100), 10);
  assert.equal(deltaPct(90, 100), -10);
  assert.equal(deltaPct(100, 100), 0);
});

test("deltaPct: guards a zero / non-finite reference with null (no Infinity/NaN leaks)", () => {
  assert.equal(deltaPct(5, 0), null);
  assert.equal(deltaPct(5, Number.NaN), null);
  assert.equal(deltaPct(5, Number.POSITIVE_INFINITY), null);
});

// ---------------------------------------------------------------------------
// predict — the model that paints the timeline
// ---------------------------------------------------------------------------

test("predict: at year 0 the behavioural ramp is zero, so mode shares equal today's split", () => {
  // ramp(0) = 0 → no car suppression yet under any scenario.
  const base = predict(0, BASELINE_SCENARIO, C);
  assert.ok(
    Math.abs(base.carShareIntoCbd - ASSUMPTIONS.modeSplit0.car) < 1e-9,
    "baseline year-0 car share equals modeSplit0.car",
  );
  const charge = predict(0, CHARGE, C);
  assert.ok(
    Math.abs(charge.carShareIntoCbd - ASSUMPTIONS.modeSplit0.car) < 1e-9,
    "charge year-0 car share equals modeSplit0.car (response has not started)",
  );
  assert.equal(base.publicRealm, 0, "no public realm delivered on day one");
  assert.ok(Math.abs(base.support - 0.5) < 1e-9, "baseline day-one support is the 0.5 prior");
});

test("predict: clamps the year to the 0–10 horizon at both ends", () => {
  assert.deepEqual(predict(-5, CHARGE, C), predict(0, CHARGE, C));
  assert.deepEqual(predict(20, CHARGE, C), predict(10, CHARGE, C));
});

test("predict: the charge suppresses car trips into the cordon vs do-nothing", () => {
  const base = predict(10, BASELINE_SCENARIO, C);
  const charge = predict(10, CHARGE, C);
  assert.ok(
    charge.carShareIntoCbd < base.carShareIntoCbd,
    "car mode share into the CBD falls under the charge",
  );
  assert.ok(charge.co2TonnesPerDay < base.co2TonnesPerDay, "citywide CO₂ falls too");
  assert.ok(charge.transitTrips > base.transitTrips, "suppressed trips shift onto transit");
});

test("predict: pedestrianisation delivers public realm slowly (~none day one, most by y6)", () => {
  assert.equal(predict(0, PED, C).publicRealm, 0, "no public realm on day one");
  // The build ramp only starts at y≈0.8, so year 1 is barely underway.
  assert.ok(predict(1, PED, C).publicRealm < 0.1 * PED.pedestrianise, "barely started by year 1");
  assert.ok(predict(6, PED, C).publicRealm > 0.5 * PED.pedestrianise, "most delivered by year 6");
});

test("predict: baseline demand drifts up with the background growth trend", () => {
  const y0 = predict(0, BASELINE_SCENARIO, C);
  const y10 = predict(10, BASELINE_SCENARIO, C);
  // Same mode share, but more absolute trips → more vehicle-km and CO₂.
  assert.ok(y10.carTripsIntoCbd > y0.carTripsIntoCbd, "more car trips as the city grows");
  assert.ok(y10.co2TonnesPerDay > y0.co2TonnesPerDay);
});

test("predict: every output stays within its documented bounds across the horizon", () => {
  for (const scenario of SCENARIOS) {
    for (let year = 0; year <= 10; year += 0.5) {
      const s = predict(year, scenario, C);
      const finite = [
        s.carTripsIntoCbd,
        s.transitTrips,
        s.walkTripsIntoCbd,
        s.vehicleKm,
        s.co2TonnesPerDay,
        s.congestion,
        s.carShareIntoCbd,
        s.publicRealm,
        s.tod,
        s.support,
      ];
      for (const v of finite) assert.ok(Number.isFinite(v), `finite ${scenario.id}@${year}`);
      assert.ok(s.carTripsIntoCbd >= 0, "trips never go negative");
      assert.ok(s.support >= 0.05 && s.support <= 0.95, "support clamp");
      assert.ok(s.congestion >= 0 && s.congestion <= 1.6, "congestion clamp");
      assert.ok(s.carShareIntoCbd >= 0 && s.carShareIntoCbd <= 1, "car share is a share");
      assert.ok(s.publicRealm >= 0 && s.publicRealm <= 1, "public realm is a share");
      assert.ok(s.tod >= 0 && s.tod <= 1, "TOD is a share");
    }
  }
});

test("predict: CO₂ is exactly the vehicle-km carried through the documented emission factor", () => {
  // Pins the provenance chain: CO₂ is not an independent guess, it is vehicle-km
  // × the single published tailpipe factor. No hidden fudge can creep in.
  const s = predict(7, CHARGE, C);
  assert.ok(
    Math.abs(s.co2TonnesPerDay - (s.vehicleKm * ASSUMPTIONS.carCo2KgPerKm) / 1000) < 1e-9,
  );
});
