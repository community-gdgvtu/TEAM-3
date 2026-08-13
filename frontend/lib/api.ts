/**
 * Tiny typed client for the URBAN backend.
 *
 * The base URL comes from `NEXT_PUBLIC_API_BASE_URL` so the same build can point
 * at local dev or a deployed backend. All values returned by the twin are tagged
 * Observed/Estimated/Simulated/Generated per SPEC §34; this module only carries
 * the liveness probe for now.
 */

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export interface Health {
  status: string;
  service: string;
  version: string;
  environment: string;
  llm_enabled: boolean;
}

/** Fetch the backend liveness probe. Throws on network/HTTP error. */
export async function getHealth(signal?: AbortSignal): Promise<Health> {
  const res = await fetch(`${API_BASE_URL}/health`, {
    signal,
    // Always hit the live backend; never serve a stale cached health status.
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Backend returned HTTP ${res.status}`);
  }
  return (await res.json()) as Health;
}

// ---------------------------------------------------------------------------
// Policy compiler (SPEC §3) — POST /policy/compile
// ---------------------------------------------------------------------------

/**
 * The structured Policy DSL is deliberately typed loosely on the client: the
 * backend (`app/policy/dsl.py`) owns the authoritative schema, and the editable
 * assumptions panel reads/writes fields by dotted path rather than by a fixed
 * shape. Keeping it as a nested record avoids the two schemas drifting.
 */
export type PolicyDSL = Record<string, unknown>;

/**
 * One extracted/inferred field surfaced for human correction. Per SPEC §3 the
 * compiler must "display every extracted assumption … never bury assumptions
 * inside prompts", so each carries where it came from and how sure we are.
 */
export interface Assumption {
  /** Dotted path into the DSL, e.g. `intervention.amount`. */
  field: string;
  /** The value the compiler chose (scalar, array, or nested object). */
  value: unknown;
  /** `stated` (verbatim), `inferred` (derived), or `default` (not in text). */
  source: "stated" | "inferred" | "default" | string;
  /** 0..1 confidence. */
  confidence: number;
  /** Short human-readable justification. */
  rationale: string;
}

export interface CompileResponse {
  policy: PolicyDSL;
  assumptions: Assumption[];
  /** `"llm"` or `"rule_based"`. */
  method: string;
  /** Always `"Generated"` — the DSL is machine-produced (SPEC §34). */
  provenance: string;
  warnings: string[];
}

export interface CompileRequest {
  text: string;
  jurisdiction?: string;
}

/** Compile natural-language policy text into a Policy DSL. Throws on error. */
export async function compilePolicy(
  req: CompileRequest,
  signal?: AbortSignal,
): Promise<CompileResponse> {
  const res = await fetch(`${API_BASE_URL}/policy/compile`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
    signal,
    cache: "no-store",
  });
  if (!res.ok) {
    let detail = `Backend returned HTTP ${res.status}`;
    try {
      const body = (await res.json()) as { detail?: unknown };
      if (typeof body.detail === "string") detail = body.detail;
    } catch {
      // Non-JSON error body; keep the generic message.
    }
    throw new Error(detail);
  }
  return (await res.json()) as CompileResponse;
}
