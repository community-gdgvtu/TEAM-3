"use client";

/**
 * Run reproducibility view (SPEC §32): the "REPRODUCE RUN" affordance made real.
 *
 * `POST /reproduce` returns the full manifest behind a run — dataset versions
 * (content-addressed by file bytes), model versions pinned to their code, the
 * live assumption set, seed, code version, and a self-verified `output_digest`.
 * The headline artifact is the `run_id`: a SHA-256 content hash of the exact
 * reproducing inputs (timestamp excluded), so identical inputs always yield the
 * same key. `reproducible` is *proven*, not asserted — the backend runs the
 * deterministic core twice and compares digests.
 *
 * The honesty story (SPEC §32/§34): this is not a simulation output, it is
 * Observed *about* the run. `prompts` is always empty because no LLM enters the
 * numeric path. When the backend is down we say so rather than minting a fake
 * key — a fabricated content address would be the exact opposite of the point.
 */

import { useEffect, useState } from "react";

import { runReproduce } from "../../lib/api";
import type {
  AssumptionRecord,
  DatasetVersion,
  ModelVersion,
  ReproManifest,
} from "../../lib/api";
import { useTwin } from "./TwinStore";

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

export default function ReproducePanel() {
  const { policy } = useTwin();
  const [status, setStatus] = useState<Status>("idle");
  const [manifest, setManifest] = useState<ReproManifest | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [showAssumptions, setShowAssumptions] = useState(false);

  // A fresh/edited policy invalidates any prior manifest — its run_id no longer
  // describes the current inputs.
  useEffect(() => {
    setManifest(null);
    setStatus("idle");
    setError(null);
    setCopied(false);
  }, [policy]);

  async function run() {
    if (!policy) return;
    setStatus("loading");
    setError(null);
    setCopied(false);
    try {
      const m = await runReproduce(policy);
      setManifest(m);
      setStatus("ready");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Reproducibility manifest failed");
      setStatus("error");
    }
  }

  function copyRunId() {
    if (!manifest) return;
    const nav = typeof navigator !== "undefined" ? navigator : undefined;
    if (nav?.clipboard?.writeText) {
      nav.clipboard.writeText(manifest.run_id).then(
        () => {
          setCopied(true);
          window.setTimeout(() => setCopied(false), 1600);
        },
        () => setCopied(false),
      );
    }
  }

  const promptsClean = manifest ? manifest.prompts.length === 0 : false;
  const anyLlmNumbers = manifest
    ? manifest.models.some((m) => m.llm_touches_numbers)
    : false;

  return (
    <section className="card reproduce">
      <div className="dashboard-head">
        <h2>Reproducibility</h2>
        <span className="dashboard-sub">
          REPRODUCE RUN · content-addressed manifest, no AI astrology (SPEC §32)
        </span>
      </div>

      {!policy ? (
        <div className="waiting">
          <span className="tag muted">No policy yet</span>
          <p>
            Compile a policy above to pin its run: dataset + model versions, the
            live assumption set, seed and code version, plus a content-addressed{" "}
            <code>run_id</code> and a self-verified output digest proving the
            deterministic core reproduces byte-for-byte.
          </p>
        </div>
      ) : (
        <>
          <div className="policy-actions" style={{ marginTop: 0 }}>
            <button
              type="button"
              className="btn primary"
              onClick={run}
              disabled={status === "loading"}
            >
              {status === "loading"
                ? "Pinning the run…"
                : manifest
                  ? "Re-pin run"
                  : "Build manifest"}
            </button>
            {manifest && (
              <span className={`tag ${manifest.provenance.toLowerCase()}`}>
                {manifest.provenance} (about the run)
              </span>
            )}
          </div>

          {status === "error" && (
            <p className="hint error-text">
              Couldn&rsquo;t build the manifest: {error}. No key is invented —
              reconnect the backend to pin the run.
            </p>
          )}

          {status === "idle" && !manifest && (
            <p className="hint">
              Hashes the exact inputs that determine this run (policy DSL, seed,
              dataset content, code version, live assumptions) into a stable{" "}
              <code>run_id</code>, then executes the deterministic core twice to
              prove the output digest is identical. Click to build.
            </p>
          )}

          {manifest && status !== "loading" && (
            <div className="repro-body">
              {/* The reproduction key — the headline artifact */}
              <div className="repro-key">
                <div className="repro-key-head">
                  <span className="repro-key-label">run_id</span>
                  <span
                    className={`repro-verdict ${manifest.reproducible ? "ok" : "bad"}`}
                    title="Deterministic core executed twice; output digests compared"
                  >
                    {manifest.reproducible
                      ? "✓ reproducible"
                      : "✗ not reproducible"}
                  </span>
                </div>
                <div className="repro-key-row">
                  <code className="repro-hash repro-runid">{manifest.run_id}</code>
                  <button type="button" className="repro-copy" onClick={copyRunId}>
                    {copied ? "copied ✓" : "copy"}
                  </button>
                </div>
                <div className="repro-key-meta">
                  <span title="SHA-256 of the canonical simulation outputs">
                    <span className="repro-meta-label">output digest</span>{" "}
                    <code className="repro-hash">
                      {manifest.output_digest.slice(0, 16)}…
                    </code>
                  </span>
                  <span>
                    <span className="repro-meta-label">code</span>{" "}
                    <code className="repro-hash">{manifest.code_version}</code>
                  </span>
                  <span>
                    <span className="repro-meta-label">app</span> v
                    {manifest.app_version}
                  </span>
                  <span>
                    <span className="repro-meta-label">seed</span>{" "}
                    {manifest.seed ?? "—"}
                  </span>
                  <span>
                    <span className="repro-meta-label">created</span>{" "}
                    {manifest.created_at}
                  </span>
                </div>
              </div>

              {manifest.how_to_reproduce && (
                <p className="hint repro-howto">{manifest.how_to_reproduce}</p>
              )}

              {/* SPEC §34 honesty line: no LLM on the numeric path */}
              <div className={`repro-guardrail ${promptsClean && !anyLlmNumbers ? "ok" : "bad"}`}>
                <span className="repro-gr-mark" aria-hidden>
                  {promptsClean && !anyLlmNumbers ? "✓" : "✗"}
                </span>
                <span>
                  {promptsClean
                    ? "No LLM prompt entered the numeric path"
                    : `${manifest.prompts.length} prompt(s) recorded on the numeric path`}
                  {" · "}
                  {anyLlmNumbers
                    ? "a model reports LLM-touched numbers"
                    : "every pinned model is model-only for numbers"}{" "}
                  (SPEC §34)
                </span>
              </div>

              {/* Datasets — content-addressed world state */}
              <h3 className="repro-sub">Datasets · {manifest.datasets.length}</h3>
              <div className="repro-datasets">
                {manifest.datasets.map((d) => (
                  <DatasetRow key={d.id} d={d} />
                ))}
              </div>

              {/* Model versions pinned to code */}
              <h3 className="repro-sub">Model versions · {manifest.models.length}</h3>
              <div className="repro-models">
                {manifest.models.map((m) => (
                  <ModelRow key={m.id} m={m} />
                ))}
              </div>

              {/* Live assumption set (collapsible; can be long) */}
              {manifest.assumptions.length > 0 && (
                <>
                  <h3 className="repro-sub">
                    Pinned assumptions · {manifest.assumptions.length}
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
                    <div
                      className="repro-assumptions"
                      role="table"
                      aria-label="Pinned assumption values"
                    >
                      <div className="repro-arow repro-arow-head" role="row">
                        <span role="columnheader">Assumption</span>
                        <span role="columnheader">Value</span>
                        <span role="columnheader">Source</span>
                        <span role="columnheader">Tag</span>
                      </div>
                      {manifest.assumptions.map((a) => (
                        <AssumptionRow key={a.name} a={a} />
                      ))}
                    </div>
                  )}
                </>
              )}

              <p className="hint repro-note">{manifest.note}</p>
            </div>
          )}
        </>
      )}
    </section>
  );
}

function DatasetRow({ d }: { d: DatasetVersion }) {
  const missing = d.content_sha256 === "MISSING";
  return (
    <div className="repro-dataset">
      <div className="repro-ds-head">
        <span className="repro-ds-name">{d.name}</span>
        <span className={`reg-badge kind ${d.kind}`}>{d.kind}</span>
        <span className={`tag ${d.provenance.toLowerCase()}`}>{d.provenance}</span>
      </div>
      <div className="repro-ds-meta">
        <code className="repro-ds-path">{d.path}</code>
        {d.seed != null && (
          <span className="repro-ds-seed">seed {fmtValue(d.seed)}</span>
        )}
      </div>
      <code className={`repro-hash repro-ds-hash${missing ? " missing" : ""}`}>
        {missing ? "⚠ dataset file not found" : `sha256:${d.content_sha256}`}
      </code>
    </div>
  );
}

function ModelRow({ m }: { m: ModelVersion }) {
  const safe = !m.llm_touches_numbers;
  return (
    <div className="repro-model">
      <div className="repro-model-head">
        <span className="repro-model-name">{m.name}</span>
        <div className="repro-model-tags">
          {m.spec_sections.map((s) => (
            <span className="reg-spec" key={s}>
              {s}
            </span>
          ))}
          <span className={`tag ${m.output_tag.toLowerCase()}`}>{m.output_tag}</span>
        </div>
      </div>
      <div className="repro-model-badges">
        <span className={`reg-badge ${m.determinism.startsWith("deter") ? "det" : "stoch"}`}>
          {m.determinism}
        </span>
        <span
          className={`reg-badge llm ${safe ? "safe" : "danger"}`}
          title="SPEC §34: LLMs must never emit core numeric effects"
        >
          {safe ? "numbers: model only" : "⚠ LLM touches numbers"}
        </span>
      </div>
      <code className="repro-model-code">{m.code}</code>
    </div>
  );
}

function AssumptionRow({ a }: { a: AssumptionRecord }) {
  return (
    <div className="repro-arow" role="row">
      <span role="cell" className="repro-aname" title={a.name}>
        {a.label}
      </span>
      <span role="cell" className="repro-aval">
        {fmtValue(a.value)}
        {a.unit ? ` ${a.unit}` : ""}
      </span>
      <span role="cell" className="repro-asrc" title={a.source}>
        {a.source}
      </span>
      <span role="cell">
        <span className={`tag ${a.tag.toLowerCase()}`}>{a.tag}</span>
      </span>
    </div>
  );
}
