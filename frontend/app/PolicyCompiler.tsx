"use client";

import { useState } from "react";
import {
  compilePolicy,
  type Assumption,
  type CompileResponse,
  type PolicyDSL,
} from "@/lib/api";
import { fieldKind, getByPath, setByPath } from "@/lib/dsl";

/** Prefilled demo policy matching the ROADMAP demo scenario. */
const DEMO_POLICY =
  "Charge private vehicles 12 credits to enter the central business district " +
  "between 7am and 7pm on weekdays, starting 2026-01-01. Exempt buses, taxis, " +
  "and blue-badge holders. Spend 70% of the revenue on public transport and " +
  "20% on cycling and walking. The aim is to cut congestion and emissions " +
  "without raising costs for low-income residents by more than 5%.";

type State =
  | { kind: "idle" }
  | { kind: "loading" }
  | { kind: "error"; message: string }
  | { kind: "ok"; result: CompileResponse; policy: PolicyDSL };

/**
 * Policy input box + editable extracted-assumptions panel (SPEC §3, M1).
 *
 * The user drafts a policy in plain language; the backend compiler returns the
 * structured Policy DSL plus a list of assumptions (each tagged stated /
 * inferred / default with a confidence). Every assumption is rendered as an
 * editable control so a human can correct anything the compiler guessed —
 * "never bury assumptions inside prompts". The edited DSL is what downstream
 * milestones (baseline vs. policy simulation) will consume.
 */
export default function PolicyCompiler() {
  const [text, setText] = useState(DEMO_POLICY);
  const [state, setState] = useState<State>({ kind: "idle" });

  async function onCompile() {
    const trimmed = text.trim();
    if (!trimmed) {
      setState({ kind: "error", message: "Enter some policy text first." });
      return;
    }
    setState({ kind: "loading" });
    try {
      const result = await compilePolicy({ text: trimmed });
      setState({ kind: "ok", result, policy: result.policy });
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Unknown error";
      setState({ kind: "error", message });
    }
  }

  /** Apply an edit to a DSL field by dotted path, keeping the DSL in state. */
  function editField(path: string, value: unknown) {
    setState((prev) =>
      prev.kind === "ok"
        ? { ...prev, policy: setByPath(prev.policy, path, value) }
        : prev,
    );
  }

  return (
    <section className="card" aria-label="Policy compiler">
      <h2>Draft a policy</h2>
      <p className="hint" style={{ marginTop: 0 }}>
        Write the policy in plain language. The compiler extracts a structured
        rulebook and shows every assumption it made — edit anything it got wrong.
      </p>

      <textarea
        className="policy-input"
        value={text}
        onChange={(e) => setText(e.target.value)}
        rows={6}
        placeholder="e.g. Charge vehicles entering the city centre and spend the money on buses…"
        spellCheck={false}
      />

      <div className="policy-actions">
        <button
          type="button"
          className="btn primary"
          onClick={onCompile}
          disabled={state.kind === "loading"}
        >
          {state.kind === "loading" ? "Compiling…" : "Compile policy"}
        </button>
        <button
          type="button"
          className="btn"
          onClick={() => setText(DEMO_POLICY)}
          disabled={state.kind === "loading"}
        >
          Load demo policy
        </button>
      </div>

      {state.kind === "error" && (
        <p className="hint error-text">Couldn’t compile: {state.message}</p>
      )}

      {state.kind === "ok" && (
        <CompiledView
          result={state.result}
          policy={state.policy}
          onEdit={editField}
        />
      )}
    </section>
  );
}

function CompiledView({
  result,
  policy,
  onEdit,
}: {
  result: CompileResponse;
  policy: PolicyDSL;
  onEdit: (path: string, value: unknown) => void;
}) {
  return (
    <div className="compiled">
      <div className="tags">
        <span className="tag generated" title="Machine-produced structuring (SPEC §34)">
          {result.provenance}
        </span>
        <span className="tag" title="Which compiler path produced the DSL">
          {result.method === "llm" ? "LLM structuring" : "Rule-based"}
        </span>
        <span className="tag muted">{result.assumptions.length} assumptions</span>
      </div>

      {result.warnings.length > 0 && (
        <ul className="warnings">
          {result.warnings.map((w, i) => (
            <li key={i}>{w}</li>
          ))}
        </ul>
      )}

      <h3 className="assumptions-title">Extracted assumptions</h3>
      <p className="hint" style={{ marginTop: 0 }}>
        Correct any the compiler inferred or defaulted. Edits update the policy
        that later simulations will run on.
      </p>

      <ul className="assumptions">
        {result.assumptions.map((a) => (
          <AssumptionRow
            key={a.field}
            assumption={a}
            value={getByPath(policy, a.field)}
            onEdit={onEdit}
          />
        ))}
      </ul>

      <details className="dsl-json">
        <summary>Compiled Policy DSL (JSON)</summary>
        <pre>{JSON.stringify(policy, null, 2)}</pre>
      </details>
    </div>
  );
}

function AssumptionRow({
  assumption,
  value,
  onEdit,
}: {
  assumption: Assumption;
  value: unknown;
  onEdit: (path: string, value: unknown) => void;
}) {
  const { field, source, confidence, rationale } = assumption;
  // Bind the control to the live DSL value when present; otherwise fall back to
  // the value the compiler originally reported for this assumption.
  const current = value === undefined ? assumption.value : value;
  const kind = fieldKind(current);
  const pct = Math.round(confidence * 100);

  return (
    <li className="assumption">
      <div className="assumption-head">
        <code className="field">{field}</code>
        <span className={`source ${source}`}>{source}</span>
        <span className="confidence" title="Compiler confidence">
          {pct}%
        </span>
      </div>

      <div className="assumption-control">
        {kind === "boolean" && (
          <label className="switch">
            <input
              type="checkbox"
              checked={Boolean(current)}
              onChange={(e) => onEdit(field, e.target.checked)}
            />
            <span>{current ? "true" : "false"}</span>
          </label>
        )}

        {kind === "number" && (
          <input
            type="number"
            className="value-input"
            value={Number(current)}
            step="any"
            onChange={(e) => {
              const n = e.target.valueAsNumber;
              onEdit(field, Number.isNaN(n) ? 0 : n);
            }}
          />
        )}

        {kind === "list" && (
          <input
            type="text"
            className="value-input"
            value={(current as unknown[]).join(", ")}
            placeholder="comma-separated"
            onChange={(e) =>
              onEdit(
                field,
                e.target.value
                  .split(",")
                  .map((s) => s.trim())
                  .filter((s) => s.length > 0),
              )
            }
          />
        )}

        {kind === "text" && (
          <input
            type="text"
            className="value-input"
            value={current === null ? "" : String(current)}
            onChange={(e) => onEdit(field, e.target.value)}
          />
        )}

        {kind === "readonly" && (
          <code className="value-readonly">{JSON.stringify(current)}</code>
        )}
      </div>

      {rationale && <p className="rationale">{rationale}</p>}
    </li>
  );
}
