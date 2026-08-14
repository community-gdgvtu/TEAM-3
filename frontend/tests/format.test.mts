/**
 * Unit tests for the shared dashboard number formatters (lib/format.ts).
 *
 * These helpers render every headline metric a judge reads, so a regression
 * here silently corrupts the numbers on screen — exactly the SPEC §34 honesty
 * surface worth guarding. Run with the repo's zero-dependency test runner:
 *   npm test   (node --test --experimental-strip-types)
 */

import { test } from "node:test";
import assert from "node:assert/strict";

import { formatNumber, formatSignedPct } from "../lib/format.ts";

test("formatNumber: millions use 2dp + M suffix", () => {
  assert.equal(formatNumber(1_500_000), "1.50M");
  assert.equal(formatNumber(12_340_000), "12.34M");
});

test("formatNumber: 10k+ uses 1dp k, sub-10k thousands use 2dp k", () => {
  assert.equal(formatNumber(12_345), "12.3k");
  assert.equal(formatNumber(1_234), "1.23k");
});

test("formatNumber: hundreds are integers, ones are 1dp, sub-1 is 2dp", () => {
  assert.equal(formatNumber(150), "150");
  assert.equal(formatNumber(4.56), "4.6");
  assert.equal(formatNumber(0.123), "0.12");
  assert.equal(formatNumber(0), "0.00");
});

test("formatNumber: threshold uses magnitude but preserves sign", () => {
  // abs picks the bucket; the original (negative) value is what gets formatted.
  assert.equal(formatNumber(-2_000_000), "-2.00M");
  assert.equal(formatNumber(-12_345), "-12.3k");
  assert.equal(formatNumber(-4.56), "-4.6");
});

test("formatSignedPct: positive gets +, uses 1dp", () => {
  assert.equal(formatSignedPct(0.042), "+4.2%");
  assert.equal(formatSignedPct(0.999), "+99.9%");
});

test("formatSignedPct: negative uses a real minus sign (U+2212), not hyphen", () => {
  const out = formatSignedPct(-0.01);
  assert.equal(out, "−1.0%");
  assert.ok(!out.includes("-"), "must not contain an ASCII hyphen-minus");
});

test("formatSignedPct: exact zero is unsigned", () => {
  assert.equal(formatSignedPct(0), "0.0%");
});
