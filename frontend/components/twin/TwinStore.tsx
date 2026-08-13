"use client";

/**
 * Shared twin state: the compiled Policy DSL (published by the compiler) and the
 * current simulation result (World A/B/Δ). Lifting these into a context lets the
 * parliament run a debate on the compiled policy and lets "apply amendment +
 * re-simulate" (SPEC §29) update the map + dashboard from one place.
 */

import { createContext, useContext, useMemo, useState } from "react";
import type { PolicyDSL, SimulateResponse } from "../../lib/api";

/** How the active simulation was produced — shown so amendments are traceable. */
export interface SimSource {
  label: string;
  amended: boolean;
}

interface TwinState {
  policy: PolicyDSL | null;
  setPolicy: (p: PolicyDSL | null) => void;
  sim: SimulateResponse | null;
  simSource: SimSource | null;
  setSim: (sim: SimulateResponse | null, source: SimSource | null) => void;
}

const TwinCtx = createContext<TwinState | null>(null);

export function TwinProvider({ children }: { children: React.ReactNode }) {
  const [policy, setPolicy] = useState<PolicyDSL | null>(null);
  const [sim, setSimState] = useState<SimulateResponse | null>(null);
  const [simSource, setSimSource] = useState<SimSource | null>(null);

  const value = useMemo<TwinState>(
    () => ({
      policy,
      setPolicy: (p) => {
        setPolicy(p);
        // A fresh/edited policy invalidates any prior simulation.
        setSimState(null);
        setSimSource(null);
      },
      sim,
      simSource,
      setSim: (s, source) => {
        setSimState(s);
        setSimSource(source);
      },
    }),
    [policy, sim, simSource],
  );

  return <TwinCtx.Provider value={value}>{children}</TwinCtx.Provider>;
}

export function useTwin(): TwinState {
  const ctx = useContext(TwinCtx);
  if (!ctx) throw new Error("useTwin must be used within a TwinProvider");
  return ctx;
}
