/**
 * Unit tests for the microsim constraint-compliance verdict (lib/api.ts
 * constraintVerdict).
 *
 * This is honesty-critical (SPEC §34): the card it drives answers "did the
 * policy keep its own stated equity promise?". The engine now tests the
 * `max_low_income_burden_increase_pct` cap against the modelled low-income
 * burden; this pure mapper must never dress a vacuous (zero-burden) pass up as
 * an actively-met promise, and must never soften a real overshoot into anything
 * but a hard fail.
 */

import { test } from "node:test";
import assert from "node:assert/strict";

import { constraintVerdict, type ConstraintCheck } from "../lib/api.ts";

function check(overrides: Partial<ConstraintCheck>): ConstraintCheck {
  return {
    name: "max_low_income_burden_increase_pct",
    cap_pct: 1,
    modelled_low_income_burden_pct: 0,
    satisfied: true,
    margin_pct: 1,
    note: "",
    provenance: "Simulated",
    ...overrides,
  };
}

test("constraintVerdict: zero modelled burden is moot, not an active pass", () => {
  const v = constraintVerdict(
    check({ modelled_low_income_burden_pct: 0, satisfied: true, margin_pct: 1 }),
  );
  assert.equal(v.status, "moot");
  assert.equal(v.cls, "good");
  assert.equal(v.label, "No low-income burden");
});

test("constraintVerdict: sub-0.005% burden rounds to moot (matches 2dp display)", () => {
  const v = constraintVerdict(
    check({ modelled_low_income_burden_pct: 0.004, satisfied: true }),
  );
  assert.equal(v.status, "moot");
});

test("constraintVerdict: real burden within cap is an active pass", () => {
  const v = constraintVerdict(
    check({
      cap_pct: 1,
      modelled_low_income_burden_pct: 0.6,
      satisfied: true,
      margin_pct: 0.4,
    }),
  );
  assert.equal(v.status, "pass");
  assert.equal(v.cls, "good");
  assert.equal(v.label, "Constraint met");
});

test("constraintVerdict: overshoot is a hard fail, never softened", () => {
  const v = constraintVerdict(
    check({
      cap_pct: 1,
      modelled_low_income_burden_pct: 1.8,
      satisfied: false,
      margin_pct: -0.8,
    }),
  );
  assert.equal(v.status, "fail");
  assert.equal(v.cls, "warn");
  assert.equal(v.label, "Constraint violated");
});

test("constraintVerdict: a nonzero burden the engine flags unsatisfied fails even at the boundary", () => {
  // Trust the engine's `satisfied` flag (which carries the cap+epsilon logic)
  // rather than re-deriving it from cap_pct here.
  const v = constraintVerdict(
    check({
      cap_pct: 1,
      modelled_low_income_burden_pct: 1.0,
      satisfied: false,
      margin_pct: 0,
    }),
  );
  assert.equal(v.status, "fail");
});
