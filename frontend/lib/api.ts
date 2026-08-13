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
