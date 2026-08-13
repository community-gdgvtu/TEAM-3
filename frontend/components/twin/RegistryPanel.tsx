"use client";

/**
 * Model registry / transparency view (SPEC §33): the machine-readable answer to
 * "how do we know these numbers aren't AI astrology?". `GET /registry` returns a
 * self-describing manifest — every forecast layer with its method, determinism
 * class, LLM role, and output tag; the data sources it reads; the flat index of
 * live assumption values (read from the code, so they can't drift); and the SPEC
 * §34 guardrail checklist with a pass/fail for each rule.
 *
 * This tab is policy-independent (it describes the engine, not a run) and loads
 * on mount. It is itself Observed — it describes code, it doesn't simulate. The
 * headline honesty artifact is the guardrail checklist: it shows, concretely, how
 * LLMs are kept off the numeric path. If the backend is down we say so rather than
 * pretending the guardrails hold.
 */

import { useEffect, useState } from "react";

import { getRegistry } from "../../lib/api";
import type {
  AssumptionRecord,
  DataSourceCard,
  GuardrailCheck,
  ModelCard,
  ModelRegistry,
} from "../../lib/api";

type Status = "idle" | "loading" | "ready" | "error";

/** Render any JSON assumption value compactly. */
function fmtValue(v: unknown): string {
  if (v === null || v === undefined) return "—";
  if (typeof v === "number") return String(v);
  if (typeof v === "boolean") return v ? "true" : "false";
  if (typeof v === "string") return v;
  try {
    return JSON.stringify(v);
  } catch {
    return String(v);
  }
}

export default function RegistryPanel() {
  const [reg, setReg] = useState<ModelRegistry | null>(null);
  const [status, setStatus] = useState<Status>("idle");
  const [error, setError] = useState<string | null>(null);
  const [showAssumptions, setShowAssumptions] = useState(false);

  function load(signal?: AbortSignal) {
    setStatus("loading");
    setError(null);
    getRegistry(signal)
      .then((r) => {
        setReg(r);
        setStatus("ready");
      })
      .catch((e: unknown) => {
        if (signal?.aborted) return;
        setError(e instanceof Error ? e.message : "Registry unavailable");
        setStatus("error");
      });
  }

  useEffect(() => {
    const ctrl = new AbortController();
    load(ctrl.signal);
    return () => ctrl.abort();
  }, []);

  const guardrailsPass =
    reg && reg.guardrails.length > 0 && reg.guardrails.every((g) => g.holds);

  return (
    <section className="card registry">
      <div className="dashboard-head">
        <h2>Model registry</h2>
        <span className="dashboard-sub">
          Transparency manifest · how the numbers are made, no AI astrology (SPEC §33)
        </span>
      </div>

      {status === "loading" && !reg && (
        <p className="hint">Loading the transparency manifest from the backend…</p>
      )}

      {status === "error" && (
        <div className="waiting">
          <span className="tag muted">Backend unavailable</span>
          <p>
            Couldn&rsquo;t load the model registry: {error}. Nothing here is
            invented — reconnect the backend to see the live manifest.
          </p>
          <button type="button" className="btn" onClick={() => load()}>
            Retry
          </button>
        </div>
      )}

      {reg && (
        <div className="reg-body">
          <div className="reg-topline">
            <span className={`tag ${reg.provenance.toLowerCase()}`}>{reg.provenance}</span>
            <span className="reg-ver">v{reg.app_version}</span>
            <span className="reg-gen">assumptions: {reg.generated_from}</span>
          </div>
          <p className="hint reg-note">{reg.note}</p>

          {/* Summary counts */}
          {Object.keys(reg.counts).length > 0 && (
            <div className="reg-counts">
              {Object.entries(reg.counts).map(([k, v]) => (
                <div className="reg-count" key={k}>
                  <span className="reg-count-val">{v}</span>
                  <span className="reg-count-label">{k.replace(/_/g, " ")}</span>
                </div>
              ))}
            </div>
          )}

          {/* Guardrail checklist — the headline honesty artifact */}
          <h3 className="reg-sub">
            SPEC §34 guardrails
            <span
              className={`reg-gr-summary ${guardrailsPass ? "ok" : "bad"}`}
              title="All anti-AI-astrology guardrails satisfied by this build"
            >
              {guardrailsPass
                ? `all ${reg.guardrails.length} enforced ✓`
                : "some not enforced ✗"}
            </span>
          </h3>
          <div className="reg-guardrails">
            {reg.guardrails.map((g) => (
              <GuardrailRow key={g.id} g={g} />
            ))}
          </div>

          {/* Model cards */}
          <h3 className="reg-sub">Forecast layers · {reg.models.length}</h3>
          <div className="reg-models">
            {reg.models.map((m) => (
              <ModelCardView key={m.id} m={m} />
            ))}
          </div>

          {/* Data sources */}
          {reg.data_sources.length > 0 && (
            <>
              <h3 className="reg-sub">Data sources · {reg.data_sources.length}</h3>
              <div className="reg-sources">
                {reg.data_sources.map((d) => (
                  <DataSourceView key={d.id} d={d} />
                ))}
              </div>
            </>
          )}

          {/* Assumption index (collapsible; can be long) */}
          {reg.assumption_index.length > 0 && (
            <>
              <h3 className="reg-sub">
                Assumption index · {reg.assumption_index.length}
                <button
                  type="button"
                  className="reg-toggle"
                  onClick={() => setShowAssumptions((s) => !s)}
                  aria-expanded={showAssumptions}
                >
                  {showAssumptions ? "hide" : "show all"}
                </button>
              </h3>
              {showAssumptions && (
                <div className="reg-assumptions" role="table" aria-label="Live assumption values">
                  <div className="reg-arow reg-arow-head" role="row">
                    <span role="columnheader">Assumption</span>
                    <span role="columnheader">Value</span>
                    <span role="columnheader">Source</span>
                    <span role="columnheader">Tag</span>
                  </div>
                  {reg.assumption_index.map((a) => (
                    <AssumptionRow key={a.name} a={a} />
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      )}
    </section>
  );
}

function GuardrailRow({ g }: { g: GuardrailCheck }) {
  return (
    <div className={`reg-gr ${g.holds ? "ok" : "bad"}`}>
      <span className="reg-gr-mark" aria-hidden>
        {g.holds ? "✓" : "✗"}
      </span>
      <div className="reg-gr-text">
        <p className="reg-gr-rule">{g.rule}</p>
        <p className="reg-gr-by">
          <span className="reg-gr-by-label">enforced by</span> {g.enforced_by}
        </p>
      </div>
    </div>
  );
}

function ModelCardView({ m }: { m: ModelCard }) {
  // The single most important honesty signal per card: does an LLM touch numbers?
  const numericSafe = m.produces_numbers ? !m.llm_touches_numbers : true;
  return (
    <div className="reg-model">
      <div className="reg-model-head">
        <span className="reg-model-name">{m.name}</span>
        <div className="reg-model-tags">
          {m.spec_sections.map((s) => (
            <span className="reg-spec" key={s}>
              {s}
            </span>
          ))}
          <span className={`tag ${m.output_tag.toLowerCase()}`}>{m.output_tag}</span>
        </div>
      </div>

      <div className="reg-model-badges">
        <span className={`reg-badge ${m.determinism.startsWith("deter") ? "det" : "stoch"}`}>
          {m.determinism}
        </span>
        <span className="reg-badge layer">{m.layer}</span>
        <span
          className={`reg-badge llm ${numericSafe ? "safe" : "danger"}`}
          title="SPEC §34: LLMs must never emit core numeric effects"
        >
          {m.produces_numbers
            ? m.llm_touches_numbers
              ? "⚠ LLM touches numbers"
              : "numbers: model only"
            : "no numbers emitted"}
        </span>
        <span className="reg-badge llmrole">LLM role: {m.llm_role}</span>
      </div>

      <p className="reg-model-method">{m.method}</p>

      {(m.inputs.length > 0 || m.outputs.length > 0) && (
        <p className="reg-io">
          {m.inputs.length > 0 && (
            <>
              <span className="reg-io-label">in</span> {m.inputs.join(", ")}
            </>
          )}
          {m.outputs.length > 0 && (
            <>
              {" "}
              <span className="reg-io-label">out</span> {m.outputs.join(", ")}
            </>
          )}
        </p>
      )}

      {m.assumptions.length > 0 && (
        <div className="reg-model-assumptions">
          {m.assumptions.map((a) => (
            <span className="reg-chip" key={a.name} title={`${a.source} (${a.tag})`}>
              {a.label}: <strong>{fmtValue(a.value)}</strong>
              {a.unit ? ` ${a.unit}` : ""}
            </span>
          ))}
        </div>
      )}

      <p className="reg-code">{m.code}</p>
    </div>
  );
}

function DataSourceView({ d }: { d: DataSourceCard }) {
  return (
    <div className="reg-source">
      <div className="reg-source-head">
        <span className="reg-source-name">{d.name}</span>
        <span className={`reg-badge kind ${d.kind}`}>{d.kind}</span>
        <span className={`tag ${d.tag.toLowerCase()}`}>{d.tag}</span>
      </div>
      <p className="reg-source-desc">{d.description}</p>
      {d.used_by.length > 0 && (
        <p className="reg-source-usedby">used by {d.used_by.length} model(s)</p>
      )}
    </div>
  );
}

function AssumptionRow({ a }: { a: AssumptionRecord }) {
  return (
    <div className="reg-arow" role="row">
      <span role="cell" className="reg-aname" title={a.name}>
        {a.label}
      </span>
      <span role="cell" className="reg-aval">
        {fmtValue(a.value)}
        {a.unit ? ` ${a.unit}` : ""}
      </span>
      <span role="cell" className="reg-asrc" title={a.source}>
        {a.source}
      </span>
      <span role="cell">
        <span className={`tag ${a.tag.toLowerCase()}`}>{a.tag}</span>
      </span>
    </div>
  );
}
