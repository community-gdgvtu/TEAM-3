"use client";

/**
 * Scenario presets — the discoverable menu of canonical demo policies
 * (SPEC §3/§27/§28). `GET /scenarios` returns a curated library of ready-to-run
 * policies; every other endpoint first requires the caller to author or compile
 * a Policy DSL, so nothing advertised the demo's *own* canonical scenarios for a
 * judge (or the UI) to one-click load. This tab closes that gap: it is the twin's
 * on-ramp — browse the menu, pick a lever, load it into the workspace, and every
 * downstream panel (Parliament, Simulate, Compare, …) lights up against it.
 *
 * Honesty (SPEC §34): the catalogue is Observed *about itself* (a curated list of
 * inputs). Each card embeds the **real** compiler output — `compiled.provenance`
 * is Generated (the compiler structures text into a DSL, it never produces
 * numeric effects). Loading a scenario publishes its compiled DSL to the shared
 * store, exactly as if you had typed the prompt and pressed Compile: no numbers
 * are minted here — the quantitative figures come downstream from the
 * deterministic simulation layers. If the backend is down we say so and show
 * nothing invented.
 */

import { useEffect, useMemo, useState } from "react";

import { getScenarios } from "../../lib/api";
import type { ScenarioCard, ScenarioLibrary } from "../../lib/api";
import { useTwin } from "./TwinStore";

type Status = "idle" | "loading" | "ready" | "error";

/** Friendly labels for the compiler-derived intervention families. */
const FAMILY_LABELS: Record<string, string> = {
  road_pricing: "Road pricing",
  pedestrianisation: "Pedestrianisation",
  low_emission_zone: "Low-emission zone",
  parking_levy: "Parking levy",
  transit_investment: "Transit investment",
  other: "Other",
};

function familyLabel(family: string): string {
  return (
    FAMILY_LABELS[family] ??
    family.replace(/_/g, " ").replace(/^\w/, (c) => c.toUpperCase())
  );
}

export default function ScenariosPanel() {
  const { policy, setPolicy } = useTwin();
  const [lib, setLib] = useState<ScenarioLibrary | null>(null);
  const [status, setStatus] = useState<Status>("idle");
  const [error, setError] = useState<string | null>(null);
  const [family, setFamily] = useState<string>("all");
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});

  function load(signal?: AbortSignal) {
    setStatus("loading");
    setError(null);
    getScenarios(signal)
      .then((l) => {
        setLib(l);
        setStatus("ready");
      })
      .catch((e: unknown) => {
        if (signal?.aborted) return;
        setError(e instanceof Error ? e.message : "Scenarios unavailable");
        setStatus("error");
      });
  }

  useEffect(() => {
    const ctrl = new AbortController();
    load(ctrl.signal);
    return () => ctrl.abort();
  }, []);

  // Which scenario (if any) is the *currently active* compiled policy in the
  // store — matched by the compiled DSL itself, so the "active" badge stays
  // honest no matter how the policy got there (loaded here, or compiled in the
  // drafting box). A cheap structural compare is fine for these small DSLs.
  const activePolicyJson = useMemo(
    () => (policy ? JSON.stringify(policy) : null),
    [policy],
  );
  const activeId = useMemo(() => {
    if (!lib || !activePolicyJson) return null;
    const hit = lib.scenarios.find(
      (s) => JSON.stringify(s.compiled.policy) === activePolicyJson,
    );
    return hit?.id ?? null;
  }, [lib, activePolicyJson]);

  const shown = useMemo<ScenarioCard[]>(() => {
    if (!lib) return [];
    if (family === "all") return lib.scenarios;
    return lib.scenarios.filter((s) => s.family === family);
  }, [lib, family]);

  function loadScenario(card: ScenarioCard) {
    // Publish the pre-compiled DSL to the shared store, exactly as the drafting
    // box does after POST /policy/compile. This resets any prior simulation so a
    // previous policy's numbers can't linger (SPEC §34) — downstream panels then
    // produce this scenario's numbers on demand.
    setPolicy(card.compiled.policy);
  }

  return (
    <section className="card scn">
      <div className="dashboard-head">
        <h2>Scenario presets</h2>
        <span className="dashboard-sub">
          The discoverable menu of canonical demo policies — one click loads a
          ready-to-run lever into the workspace (SPEC §3/§27/§28)
        </span>
      </div>

      {status === "loading" && !lib && (
        <p className="hint">Loading the scenario catalogue from the backend…</p>
      )}

      {status === "error" && (
        <div className="waiting">
          <span className="tag muted">Backend unavailable</span>
          <p>
            Couldn&rsquo;t load the scenario catalogue: {error}. Nothing here is
            invented — reconnect the backend to see the live menu from{" "}
            <code>GET /scenarios</code>.
          </p>
          <button type="button" className="btn" onClick={() => load()}>
            Retry
          </button>
        </div>
      )}

      {lib && (
        <div className="reg-body">
          <div className="reg-topline">
            <span className={`tag ${lib.provenance.toLowerCase()}`}>
              {lib.provenance}
            </span>
            <span className="reg-gen">
              {lib.count} scenarios · {lib.families.length} families
            </span>
          </div>
          <p className="hint reg-note">{lib.note}</p>

          {/* Family filter — presentation only; a readout guarantees a filter
              can never make the menu look smaller than it is. */}
          <div className="scn-controls" role="group" aria-label="Filter by family">
            <button
              type="button"
              className={`scn-fam${family === "all" ? " active" : ""}`}
              aria-pressed={family === "all"}
              onClick={() => setFamily("all")}
            >
              All
            </button>
            {lib.families.map((f) => (
              <button
                key={f}
                type="button"
                className={`scn-fam${family === f ? " active" : ""}`}
                aria-pressed={family === f}
                onClick={() => setFamily(f)}
              >
                {familyLabel(f)}
              </button>
            ))}
            <span className="scn-shown">
              showing {shown.length}/{lib.count}
            </span>
          </div>

          {shown.length === 0 ? (
            <p className="hint">No scenario in this family.</p>
          ) : (
            <div className="scn-cards">
              {shown.map((s) => (
                <ScenarioView
                  key={s.id}
                  card={s}
                  active={s.id === activeId}
                  open={!!expanded[s.id]}
                  onToggle={() =>
                    setExpanded((e) => ({ ...e, [s.id]: !e[s.id] }))
                  }
                  onLoad={() => loadScenario(s)}
                />
              ))}
            </div>
          )}
        </div>
      )}
    </section>
  );
}

function ScenarioView({
  card,
  active,
  open,
  onToggle,
  onLoad,
}: {
  card: ScenarioCard;
  active: boolean;
  open: boolean;
  onToggle: () => void;
  onLoad: () => void;
}) {
  const assumptions = card.compiled.assumptions ?? [];
  const objectiveEntries = Object.entries(card.objective ?? {});
  const constraintEntries = Object.entries(card.constraints ?? {});
  return (
    <div className={`scn-card${active ? " active" : ""}`}>
      <div className="scn-card-head">
        <h3 className="scn-card-title">{card.title}</h3>
        <div className="scn-card-tags">
          <span className="scn-fam-chip">{familyLabel(card.family)}</span>
          {card.spec_sections.map((sec) => (
            <span className="reg-spec" key={sec}>
              {sec}
            </span>
          ))}
        </div>
      </div>
      <p className="scn-card-summary">{card.summary}</p>

      {(objectiveEntries.length > 0 || constraintEntries.length > 0) && (
        <div className="scn-goals">
          {objectiveEntries.map(([k, v]) => (
            <span className="scn-goal" key={`o-${k}`}>
              <span className="scn-goal-k">{k.replace(/_/g, " ")}</span>
              <span className="scn-goal-v">{String(v)}</span>
            </span>
          ))}
          {constraintEntries.map(([k, v]) => (
            <span className="scn-goal constraint" key={`c-${k}`}>
              <span className="scn-goal-k">{k.replace(/_/g, " ")}</span>
              <span className="scn-goal-v">{String(v)}</span>
            </span>
          ))}
        </div>
      )}

      <div className="scn-card-actions">
        <button
          type="button"
          className={`btn${active ? "" : " primary"}`}
          onClick={onLoad}
          disabled={active}
          aria-disabled={active}
        >
          {active ? "✓ Loaded — active policy" : "Load into workspace"}
        </button>
        <button
          type="button"
          className="btn scn-details-btn"
          onClick={onToggle}
          aria-expanded={open}
        >
          {open ? "Hide details" : "Prompt, DSL & assumptions"}
        </button>
        <span
          className="tag generated"
          title="The compiled DSL is machine-produced — structuring, not simulation (SPEC §34)"
        >
          Generated DSL
        </span>
      </div>

      {active && (
        <p className="scn-active-note">
          This scenario is the workspace&rsquo;s active compiled policy — the
          same as typing its prompt and pressing Compile. Its numbers come
          downstream from the deterministic simulation layers; nothing is minted
          here (SPEC §34).
        </p>
      )}

      {open && (
        <div className="scn-detail">
          <div className="scn-detail-block">
            <span className="scn-detail-label">Natural-language prompt</span>
            <p className="scn-prompt">{card.text}</p>
          </div>

          <div className="scn-detail-block">
            <span className="scn-detail-label">
              Reviewable assumptions ({assumptions.length}) ·{" "}
              <span className="scn-method">{card.compiled.method}</span>
            </span>
            <ul className="scn-assumptions">
              {assumptions.map((a) => (
                <li key={a.field} className="scn-assumption">
                  <code className="scn-assumption-field">{a.field}</code>
                  <span className="scn-assumption-val">{String(a.value)}</span>
                  <span className={`scn-src scn-src-${a.source}`}>
                    {a.source}
                  </span>
                  <span className="scn-conf">
                    {Math.round(a.confidence * 100)}%
                  </span>
                </li>
              ))}
            </ul>
            {card.compiled.warnings.length > 0 && (
              <p className="scn-warnings">
                ⚠ {card.compiled.warnings.join(" · ")}
              </p>
            )}
          </div>

          <div className="scn-detail-block">
            <span className="scn-detail-label">Compiled Policy DSL</span>
            <pre className="scn-dsl">
              {JSON.stringify(card.compiled.policy, null, 2)}
            </pre>
          </div>
        </div>
      )}
    </div>
  );
}
