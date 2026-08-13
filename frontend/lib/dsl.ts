/**
 * Small helpers for reading/writing the Policy DSL by dotted path.
 *
 * The editable-assumptions panel (SPEC §3) binds each assumption to a field
 * like `intervention.amount` or `revenue_allocation.public_transport`. These
 * helpers let the UI get/set those nested values immutably without hard-coding
 * the DSL shape (which lives authoritatively in the backend).
 */

import type { PolicyDSL } from "./api";

/** Read the value at a dotted `path` in `obj`, or `undefined` if absent. */
export function getByPath(obj: unknown, path: string): unknown {
  return path.split(".").reduce<unknown>((acc, key) => {
    if (acc && typeof acc === "object" && key in (acc as Record<string, unknown>)) {
      return (acc as Record<string, unknown>)[key];
    }
    return undefined;
  }, obj);
}

/**
 * Return a deep-cloned copy of `obj` with the value at dotted `path` set to
 * `value`. Intermediate objects are created as needed. The input is never
 * mutated, so it's safe to use directly in React state updates.
 */
export function setByPath(obj: PolicyDSL, path: string, value: unknown): PolicyDSL {
  const keys = path.split(".");
  // structuredClone is available in all evergreen browsers and Node 18+.
  const clone: PolicyDSL = structuredClone(obj);
  let cursor: Record<string, unknown> = clone as Record<string, unknown>;
  for (let i = 0; i < keys.length - 1; i += 1) {
    const key = keys[i];
    const next = cursor[key];
    if (!next || typeof next !== "object") {
      cursor[key] = {};
    }
    cursor = cursor[key] as Record<string, unknown>;
  }
  cursor[keys[keys.length - 1]] = value;
  return clone;
}

/** A coarse editor kind chosen from a value's runtime type. */
export type FieldKind = "boolean" | "number" | "list" | "text" | "readonly";

/** Pick which input control fits a value in the assumptions panel. */
export function fieldKind(value: unknown): FieldKind {
  if (typeof value === "boolean") return "boolean";
  if (typeof value === "number") return "number";
  if (Array.isArray(value)) return "list";
  if (value === null || typeof value === "string") return "text";
  // Nested objects are edited via their own leaf assumptions, not here.
  return "readonly";
}
