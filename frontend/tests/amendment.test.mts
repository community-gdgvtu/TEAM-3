/**
 * Unit tests for the client-side amendment helper (lib/api.ts applyAmendment).
 *
 * This is honesty-critical (SPEC §34) and correctness-critical: it is the pure
 * transform behind the "apply amendment + re-simulate" loop (SPEC §29, the killer
 * interaction) and behind the Robustness tab's candidate slate (M38), where each
 * design variant is an applyAmendment(policy, …) that the backend then simulates
 * through the deterministic A/B/Δ core. If this produces the wrong DSL — a leaked
 * mutation of the base policy, a duplicated exemption, a mis-rounded charge, or a
 * revenue split that doesn't sum to 1 — the app sends the backend a policy that
 * isn't the one the label claims, and every downstream number is silently for the
 * wrong world. The function is pure, so we pin it directly. Zero new deps.
 */

import { test } from "node:test";
import assert from "node:assert/strict";

import { applyAmendment, type Amendment, type PolicyDSL } from "../lib/api.ts";

const basePolicy = (): PolicyDSL =>
  ({
    id: "cordon_v1",
    intervention: { type: "cordon", amount: 5 },
    revenue_allocation: { public_transport: 0.8, general_fund: 0.2 },
    exemptions: ["blue-badge"],
  }) as unknown as PolicyDSL;

test("applyAmendment: never mutates the input policy (re-simulate is side-effect-free)", () => {
  const orig = basePolicy();
  const snapshot = JSON.parse(JSON.stringify(orig));
  applyAmendment(orig, { label: "Half charge", charge_multiplier: 0.5 });
  assert.deepEqual(orig, snapshot, "base policy is untouched after amending");
});

test("applyAmendment: derives a labelled id with spaces slugged to underscores", () => {
  const out = applyAmendment(basePolicy(), { label: "Low income exempt" }) as Record<
    string,
    unknown
  >;
  assert.equal(out.id, "cordon_v1__Low_income_exempt");
});

test("applyAmendment: set_charge_amount replaces the charge outright", () => {
  const out = applyAmendment(basePolicy(), { label: "Higher", set_charge_amount: 8 }) as Record<
    string,
    unknown
  >;
  assert.equal((out.intervention as Record<string, unknown>).amount, 8);
});

test("applyAmendment: charge_multiplier scales the existing charge, rounded to 4dp", () => {
  const out = applyAmendment(basePolicy(), {
    label: "Two thirds",
    charge_multiplier: 1 / 3,
  }) as Record<string, unknown>;
  // 5 * (1/3) = 1.6666… → rounded to 1.6667, not a raw float tail.
  assert.equal((out.intervention as Record<string, unknown>).amount, 1.6667);
});

test("applyAmendment: set_charge_amount then multiplier compose (multiplier hits the new amount)", () => {
  const out = applyAmendment(basePolicy(), {
    label: "Set then half",
    set_charge_amount: 10,
    charge_multiplier: 0.5,
  }) as Record<string, unknown>;
  assert.equal((out.intervention as Record<string, unknown>).amount, 5);
});

test("applyAmendment: exemptions append without duplicating an existing one (case-insensitive)", () => {
  const out = applyAmendment(basePolicy(), {
    label: "Exempt",
    exempt_low_income: true,
    exempt_residents: true,
  }) as Record<string, unknown>;
  assert.deepEqual(out.exemptions, ["blue-badge", "low-income", "residents"]);

  // Re-applying to a policy that already lists an income exemption must not double it.
  const already = { ...basePolicy(), exemptions: ["Low-Income households"] } as unknown as PolicyDSL;
  const out2 = applyAmendment(already, {
    label: "Exempt again",
    exempt_low_income: true,
  }) as Record<string, unknown>;
  assert.deepEqual(out2.exemptions, ["Low-Income households"], "no duplicate income exemption");
});

test("applyAmendment: revenue split is rewritten to sum to exactly 1", () => {
  const out = applyAmendment(basePolicy(), {
    label: "General fund",
    set_public_transport_share: 0.3,
  }) as Record<string, unknown>;
  const alloc = out.revenue_allocation as { public_transport: number; general_fund: number };
  assert.equal(alloc.public_transport, 0.3);
  assert.equal(alloc.general_fund, 0.7);
  assert.equal(alloc.public_transport + alloc.general_fund, 1);
});

test("applyAmendment: tolerates a policy with no intervention or exemptions block", () => {
  const bare = { id: "bare" } as unknown as PolicyDSL;
  const out = applyAmendment(bare, {
    label: "Add charge",
    set_charge_amount: 4,
    exempt_residents: true,
  }) as Record<string, unknown>;
  assert.equal((out.intervention as Record<string, unknown>).amount, 4);
  assert.deepEqual(out.exemptions, ["residents"]);
});
