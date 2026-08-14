"use client";

import { useState } from "react";
import {
  compilePolicy,
  type Assumption,
  type CompileResponse,
  type PolicyDSL,
} from "@/lib/api";
import { fieldKind, getByPath, setByPath } from "@/lib/dsl";
import { useTwin } from "@/components/twin/TwinStore";

/**
 * A curated gallery of plain-language starting points, one per *distinct
 * mechanism* the engine models (SPEC §7.5). These are only prompts: clicking one
 * loads its text into the box, and nothing is claimed until the backend compiles
 * and simulates it — the UI mints no numbers (SPEC §34). The `watch` note frames
 * the mechanism and the comparison to make, never a predicted outcome, so a judge
 * knows *why* the twin's numbers differ between families without us pre-stating
 * any figure.
 */
interface ExamplePolicy {
  id: string;
  label: string;
  /** Short mechanism-family tag shown as a chip. */
  mechanism: string;
  /** What this example is for — a comparison to make, not a predicted number. */
  watch: string;
  text: string;
}

const EXAMPLE_POLICIES: ExamplePolicy[] = [
  {
    id: "cordon-charge",
    label: "Congestion charge",
    mechanism: "Cordon pricing",
    watch:
      "Every entering vehicle pays in full — the baseline against which the other " +
      "pricing mechanisms below are deliberately gentler.",
    text:
      "Introduce a charge of 12 credits on private vehicles entering the central " +
      "business district between 7am and 7pm on weekdays, starting 2026-01-01. " +
      "Exempt buses, taxis, and blue-badge holders. Spend 70% of the revenue on " +
      "public transport and 20% on cycling and walking. The aim is to cut " +
      "congestion and emissions without raising costs for low-income residents " +
      "by more than 5%.",
  },
  {
    id: "peak-shoulder-charge",
    label: "Late-start charge",
    mechanism: "Time-of-day pricing",
    watch:
      "The same 12-credit cordon, but it only switches on at 8:30am — after the " +
      "commute rush has begun — so it prices just part of the inbound peak. Watch " +
      "the twin attenuate the mode shift versus the all-day cordon, honestly " +
      "reflecting the hours the charge actually operates.",
    text:
      "Introduce a charge of 12 credits on private vehicles entering the central " +
      "business district between 8:30am and 6pm on weekdays, starting 2026-01-01. " +
      "Exempt buses, taxis, and blue-badge holders. Spend 70% of the revenue on " +
      "public transport and 20% on cycling and walking. The aim is to cut " +
      "congestion at the busiest times without pricing the whole working day.",
  },
  {
    id: "low-emission-zone",
    label: "Low-emission zone",
    mechanism: "Fleet turnover",
    watch:
      "Only non-compliant vehicles pay, and the main lever is a cleaner fleet — " +
      "watch whether the twin keeps more cars on the road than the cordon charge " +
      "while still cutting emissions intensity.",
    text:
      "Create a low-emission zone covering the central business district with a " +
      "daily levy of 12 credits on older, non-compliant vehicles, in force between " +
      "7am and 7pm on weekdays, starting 2026-01-01. Exempt buses, taxis, and " +
      "blue-badge holders. Spend the revenue on public transport. The aim is to " +
      "clean up the vehicle fleet and cut tailpipe emissions.",
  },
  {
    id: "workplace-parking-levy",
    label: "Workplace parking levy",
    mechanism: "Employer levy",
    watch:
      "Levied on employers per parking space, so only part of it reaches the " +
      "commuter — watch whether the mode shift is smaller than a cordon charge of " +
      "the same amount.",
    text:
      "Introduce a workplace parking levy of 12 credits per commuter parking space " +
      "on large employers in the central business district, starting 2026-01-01. " +
      "Spend 70% of the revenue on public transport and 20% on cycling and " +
      "walking. The aim is to fund transit and nudge commuters out of cars.",
  },
  {
    id: "pedestrianisation",
    label: "Pedestrianise the core",
    mechanism: "Access restriction",
    watch:
      "A non-pricing lever — no charge, no revenue. Watch how the twin routes the " +
      "displaced trips onto transit and active travel instead of the wallet.",
    text:
      "Pedestrianise the central business district by closing it to private " +
      "vehicles between 7am and 7pm on weekdays, starting 2026-01-01. Keep access " +
      "for buses, taxis, deliveries, and blue-badge holders. The aim is to cut " +
      "congestion and emissions and reclaim street space for people.",
  },
  {
    id: "transit-investment",
    label: "Bus-funded charge",
    mechanism: "Charge + reinvest",
    watch:
      "Same cordon charge, but every credit is ploughed back into buses — watch " +
      "the reinvestment lever push the transit shift further than the charge alone.",
    text:
      "Introduce a charge of 12 credits on private vehicles entering the central " +
      "business district between 7am and 7pm on weekdays, starting 2026-01-01. " +
      "Exempt buses, taxis, and blue-badge holders. Spend 100% of the revenue on " +
      "public transport — new bus routes and higher frequencies. The aim is to cut " +
      "car use by making transit the easy choice.",
  },
  {
    id: "active-travel-reinvest",
    label: "Charge, fund cycling",
    mechanism: "Active-travel reinvest",
    watch:
      "Same cordon charge, but the revenue builds protected cycle lanes and wider " +
      "pavements instead of buses. Watch the twin pull the nearest short-trip " +
      "commuters onto foot and bike — a different destination for the displaced " +
      "trips than the bus-funded charge, and a lever that stays neutral until the " +
      "charge actually raises revenue.",
    text:
      "Introduce a charge of 12 credits on private vehicles entering the central " +
      "business district between 7am and 7pm on weekdays, starting 2026-01-01. " +
      "Exempt buses, taxis, and blue-badge holders. Spend 80% of the revenue on " +
      "protected cycle lanes and wider pavements. The aim is to cut short car trips " +
      "by making walking and cycling the easy choice.",
  },
  {
    id: "standalone-transit",
    label: "Fund buses, no charge",
    mechanism: "Transit supply",
    watch:
      "A pure carrot — cheaper, faster, more frequent buses with no charge and no " +
      "ban. Watch the twin honour the missing stick: with no cost on driving, the " +
      "pull is mostly walk→transit, so the car drop stays at or below the transit " +
      "gain — a smaller dent in car use than any pricing scheme.",
    text:
      "Invest heavily in the bus and tram network: cut fares by a third, add new " +
      "bus routes, and raise service frequencies right across the city, starting " +
      "2026-01-01. Fund it from the general budget. The aim is to grow public " +
      "transport use and cut car dependence.",
  },
];

/** Prefilled demo policy matching the ROADMAP demo scenario (SPEC §29). */
const DEMO_POLICY = EXAMPLE_POLICIES[0].text;

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
  const [activeExample, setActiveExample] = useState<string>(
    EXAMPLE_POLICIES[0].id,
  );
  const { setPolicy } = useTwin();

  /**
   * Load an example prompt into the box. Resets any compiled result back to
   * `idle` so a previous policy's numbers can't linger under a different policy's
   * text (SPEC §34) — the user re-compiles to get real numbers for the new draft.
   */
  function loadExample(ex: ExamplePolicy) {
    setText(ex.text);
    setActiveExample(ex.id);
    setState({ kind: "idle" });
  }

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
      // Publish the compiled DSL so parliament + simulation can consume it.
      setPolicy(result.policy);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Unknown error";
      setState({ kind: "error", message });
    }
  }

  /** Apply an edit to a DSL field by dotted path, keeping the DSL in state. */
  function editField(path: string, value: unknown) {
    if (state.kind !== "ok") return;
    const policy = setByPath(state.policy, path, value);
    setState({ ...state, policy });
    // Keep the shared policy in sync so downstream re-runs use the edited DSL.
    setPolicy(policy);
  }

  return (
    <section className="card" aria-label="Policy compiler" data-tour="compiler">
      <h2>Draft a policy</h2>
      <p className="hint" style={{ marginTop: 0 }}>
        Write the policy in plain language. The compiler extracts a structured
        rulebook and shows every assumption it made — edit anything it got wrong.
      </p>

      <div className="example-gallery" role="group" aria-label="Example policies">
        <p className="hint example-gallery-hint">
          Or start from a worked example — one per mechanism the twin models.
          Loading one only fills the box; no numbers appear until you compile.
        </p>
        <div className="example-chips">
          {EXAMPLE_POLICIES.map((ex) => {
            const active = ex.id === activeExample;
            return (
              <button
                key={ex.id}
                type="button"
                className={`example-btn${active ? " active" : ""}`}
                onClick={() => loadExample(ex)}
                disabled={state.kind === "loading"}
                aria-pressed={active}
                title={ex.watch}
              >
                <span className="example-btn-label">{ex.label}</span>
                <span className="chip example-btn-mech">{ex.mechanism}</span>
              </button>
            );
          })}
        </div>
        {activeExample && (
          <p className="hint example-watch">
            {EXAMPLE_POLICIES.find((e) => e.id === activeExample)?.watch}
          </p>
        )}
      </div>

      <textarea
        className="policy-input"
        value={text}
        onChange={(e) => {
          setText(e.target.value);
          // A manual edit no longer matches any example verbatim.
          setActiveExample("");
        }}
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
