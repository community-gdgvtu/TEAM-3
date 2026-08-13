"use client";

import { useEffect, useState } from "react";
import { API_BASE_URL, getHealth, type Health } from "@/lib/api";

type State =
  | { kind: "loading" }
  | { kind: "ok"; data: Health }
  | { kind: "error"; message: string };

/**
 * Client component that pings the backend `/health` endpoint on mount and
 * renders the live liveness/config state. This is the M0 proof that the
 * frontend can reach the FastAPI backend.
 */
export default function HealthStatus() {
  const [state, setState] = useState<State>({ kind: "loading" });

  useEffect(() => {
    const controller = new AbortController();
    getHealth(controller.signal)
      .then((data) => setState({ kind: "ok", data }))
      .catch((err: unknown) => {
        if (controller.signal.aborted) return;
        const message =
          err instanceof Error ? err.message : "Unknown error";
        setState({ kind: "error", message });
      });
    return () => controller.abort();
  }, []);

  return (
    <section className="card" aria-live="polite">
      <h2>Backend connection</h2>

      {state.kind === "loading" && (
        <div className="statusline">
          <span className="dot" />
          <span>Contacting backend…</span>
        </div>
      )}

      {state.kind === "error" && (
        <>
          <div className="statusline">
            <span className="dot bad" />
            <span>Cannot reach backend</span>
          </div>
          <p className="hint">
            {state.message}. Is the API running at <code>{API_BASE_URL}</code>?
            Start it with <code>uvicorn app.main:app --reload</code> in{" "}
            <code>backend/</code>.
          </p>
        </>
      )}

      {state.kind === "ok" && (
        <>
          <div className="statusline">
            <span className="dot ok" />
            <span>
              Connected — status <strong>{state.data.status}</strong>
            </span>
          </div>
          <dl className="kv">
            <dt>Service</dt>
            <dd>{state.data.service}</dd>
            <dt>Version</dt>
            <dd>{state.data.version}</dd>
            <dt>Environment</dt>
            <dd>{state.data.environment}</dd>
            <dt>LLM layer</dt>
            <dd>
              {state.data.llm_enabled
                ? "enabled"
                : "rule-based fallback (no key)"}
            </dd>
          </dl>
        </>
      )}
    </section>
  );
}
