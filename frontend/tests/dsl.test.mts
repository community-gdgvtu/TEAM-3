/**
 * Unit tests for the Policy DSL dotted-path helpers (lib/dsl.ts).
 *
 * These back the editable-assumptions panel (SPEC §3): getByPath reads an
 * assumption, setByPath writes it *immutably* for React state, and fieldKind
 * chooses the editor control. A mutation bug here would edit the wrong world or
 * silently share state between renders, so the immutability guarantee is tested
 * explicitly. Zero-dependency runner: npm test.
 */

import { test } from "node:test";
import assert from "node:assert/strict";

import { getByPath, setByPath, fieldKind } from "../lib/dsl.ts";
import type { PolicyDSL } from "../lib/api.ts";

test("getByPath: reads nested and top-level values", () => {
  const obj = { a: { b: { c: 7 } }, x: 1 };
  assert.equal(getByPath(obj, "a.b.c"), 7);
  assert.equal(getByPath(obj, "x"), 1);
});

test("getByPath: missing key or non-object mid-path is undefined", () => {
  const obj = { a: { b: 2 } };
  assert.equal(getByPath(obj, "a.z"), undefined);
  assert.equal(getByPath(obj, "a.b.c"), undefined); // b is a number, not an object
  assert.equal(getByPath(null, "a"), undefined);
});

test("setByPath: returns a new object with the leaf updated", () => {
  const orig = { intervention: { amount: 5 } } as unknown as PolicyDSL;
  const next = setByPath(orig, "intervention.amount", 9);
  assert.equal((next as any).intervention.amount, 9);
});

test("setByPath: never mutates the input (React-safe)", () => {
  const orig = { intervention: { amount: 5 }, keep: [1, 2] } as unknown as PolicyDSL;
  const next = setByPath(orig, "intervention.amount", 9);
  assert.equal((orig as any).intervention.amount, 5, "original leaf unchanged");
  assert.notEqual(next, orig, "returns a fresh top-level object");
  assert.notEqual((next as any).intervention, (orig as any).intervention, "clones the branch");
  // Deep clone: untouched branches are independent copies, not shared references.
  assert.notEqual((next as any).keep, (orig as any).keep);
  assert.deepEqual((next as any).keep, [1, 2]);
});

test("setByPath: creates intermediate objects when the path is absent", () => {
  const orig = {} as unknown as PolicyDSL;
  const next = setByPath(orig, "revenue_allocation.public_transport", 0.6);
  assert.equal((next as any).revenue_allocation.public_transport, 0.6);
});

test("setByPath: replaces a non-object intermediate rather than crashing", () => {
  const orig = { intervention: 3 } as unknown as PolicyDSL;
  const next = setByPath(orig, "intervention.amount", 9);
  assert.deepEqual((next as any).intervention, { amount: 9 });
});

test("fieldKind: maps runtime types to editor controls", () => {
  assert.equal(fieldKind(true), "boolean");
  assert.equal(fieldKind(42), "number");
  assert.equal(fieldKind([1, 2, 3]), "list");
  assert.equal(fieldKind("cordon"), "text");
  assert.equal(fieldKind(null), "text");
  assert.equal(fieldKind({ nested: 1 }), "readonly");
});
