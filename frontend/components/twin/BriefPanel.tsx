"use client";

/**
 * Minister's Brief export (SPEC §27/§28.11/§37).
 *
 * `POST /brief` renders the North-Star answer (SPEC §37) as a single,
 * self-contained Markdown memo — the one-page document behind the dashboard.
 * It introduces **no new numeric model**: every figure in the memo is the same
 * object the standalone endpoints return (the brief reads `/north-star`, which
 * itself reuses each deterministic layer verbatim), so the memo can never
 * disagree with the tabs behind it (SPEC §34).
 *
 * This panel drives that export: pick the compiled policy (or type one), choose
 * a horizon, and get the memo back with its provenance key, word count, a
 * copy-to-clipboard and a download-`.md` action, and the memo source rendered
 * faithfully. The Markdown is shown exactly as the backend produced it — no
 * client-side reformatting that could silently change a number or drop a
 * provenance tag.
 *
 * Honesty contract (SPEC §34): numbers are Simulated/Estimated, prose is
 * Generated, transparency artifacts Observed; generated media stays labelled
 * SIMULATED inside the memo; no LLM touches a figure. Nothing is fabricated —
 * when the backend is down the panel says so and offers a retry; it never mints
 * a memo of its own.
 */

import { useState } from "react";

import { runBrief } from "../../lib/api";
import type { BriefResponse } from "../../lib/api";
import { useTwin } from "./TwinStore";

type Status = "idle" | "loading" | "ready" | "error";

/** Horizon options snap to the Time-Machine checkpoints (SPEC §27). */
const HORIZONS: Array<{ label: string; months: number }> = [
  { label: "Year 1", months: 12 },
  { label: "Year 2", months: 24 },
  { label: "Year 5", months: 60 },
  { label: "Year 10", months: 120 },
];

/** Map a legend tag to its provenance chip class (defensive on unknown tags). */
function tagClass(tag: string): string {
  const t = tag.toLowerCase();
  if (t.includes("observ")) return "observed";
  if (t.includes("estimat")) return "estimated";
  if (t.includes("simulat")) return "simulated";
  if (t.includes("generat")) return "generated";
  return "muted";
}

export default function BriefPanel() {
  const { policy } = useTwin();
  const [text, setText] = useState("");
  const [horizon, setHorizon] = useState(24);
  const [includeMedia, setIncludeMedia] = useState(true);
  const [brief, setBrief] = useState<BriefResponse | null>(null);
  const [status, setStatus] = useState<Status>("idle");
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  // Prefer the compiled policy from the store; fall back to a natural-language
  // box so the tab can drive the whole compile→brief pipeline standalone (§3).
  const usingText = !policy;

  function execute() {
    if (usingText && !text.trim()) return;
    setStatus("loading");
    setError(null);
    setCopied(false);
    const req = usingText
      ? { text: text.trim(), horizon_months: horizon, include_media: includeMedia }
      : {
          policy: policy ?? undefined,
          horizon_months: horizon,
          include_media: includeMedia,
        };
    runBrief(req)
      .then((b) => {
        setBrief(b);
        setStatus("ready");
      })
      .catch((e: unknown) => {
        setError(e instanceof Error ? e.message : "Minister's Brief export failed");
        setStatus("error");
      });
  }

  function copyMemo() {
    if (!brief) return;
    const nav = typeof navigator !== "undefined" ? navigator : undefined;
    if (nav?.clipboard?.writeText) {
      nav.clipboard.writeText(brief.markdown).then(
        () => {
          setCopied(true);
          window.setTimeout(() => setCopied(false), 1600);
        },
        () => setCopied(false),
      );
    }
  }

  function downloadMemo() {
    if (!brief || typeof window === "undefined") return;
    const blob = new Blob([brief.markdown], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `ministers-brief-${brief.policy_id}.md`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  }

  return (
    <section className="card brief" data-tour="brief">
      <div className="dashboard-head">
        <h2>Minister&rsquo;s Brief</h2>
        <span className="dashboard-sub">
          the North-Star answer as a printable Markdown memo (SPEC §27/§37)
        </span>
      </div>

      <p className="hint brief-intro">
        The memo is a <strong>layout</strong> of the North-Star answer — it
        computes <strong>no new number</strong>. Every figure is read from{" "}
        <code>/north-star</code>, which reuses each deterministic layer verbatim,
        so the brief can never disagree with the tabs behind it. Numbers are
        Simulated or Estimated; prose is Generated; generated media stays labelled
        SIMULATED; no LLM touches a figure (SPEC §34).
      </p>

      {/* Input: compiled policy from the store, or a natural-language fallback. */}
      <div className="run-controls">
        {usingText ? (
          <label className="run-textwrap">
            <span className="run-label">
              No compiled policy yet — describe one to compile &amp; brief:
            </span>
            <textarea
              className="run-text"
              rows={2}
              placeholder="e.g. Charge £12 to drive into the city centre at peak and spend it on buses"
              value={text}
              onChange={(e) => setText(e.target.value)}
            />
          </label>
        ) : (
          <p className="run-usingpolicy">
            <span className="tag generated">compiled policy</span>
            Rendering the brief for the policy compiled above.
          </p>
        )}

        <div className="run-actions">
          <label className="run-horizon">
            <span className="run-label">Headline horizon</span>
            <select
              value={horizon}
              onChange={(e) => setHorizon(Number(e.target.value))}
            >
              {HORIZONS.map((h) => (
                <option key={h.months} value={h.months}>
                  {h.label}
                </option>
              ))}
            </select>
          </label>
          <label className="brief-toggle">
            <input
              type="checkbox"
              checked={includeMedia}
              onChange={(e) => setIncludeMedia(e.target.checked)}
            />
            <span>Include SIMULATED media section</span>
          </label>
          <button
            type="button"
            className="btn primary"
            onClick={execute}
            disabled={status === "loading" || (usingText && !text.trim())}
          >
            {status === "loading"
              ? "Rendering memo…"
              : usingText
                ? "Compile & brief"
                : "Render the brief"}
          </button>
        </div>
      </div>

      {status === "loading" && !brief && (
        <p className="hint">Rendering the Minister&rsquo;s Brief from the backend…</p>
      )}

      {status === "error" && (
        <div className="waiting">
          <span className="tag muted">Backend unavailable</span>
          <p>
            Couldn&rsquo;t render the brief: {error}. Nothing here is invented —
            reconnect the backend to read the memo from one deterministic run.
          </p>
          <button type="button" className="btn" onClick={execute}>
            Retry
          </button>
        </div>
      )}

      {status === "idle" && !brief && (
        <p className="hint">
          {usingText
            ? "Describe a policy above, then render the brief."
            : "Render the brief to export the §37 answer as a one-page memo."}
        </p>
      )}

      {brief && (
        <BriefResult
          brief={brief}
          stale={status === "loading"}
          copied={copied}
          onCopy={copyMemo}
          onDownload={downloadMemo}
          tagClassFor={tagClass}
        />
      )}
    </section>
  );
}

function BriefResult({
  brief,
  stale,
  copied,
  onCopy,
  onDownload,
  tagClassFor,
}: {
  brief: BriefResponse;
  stale: boolean;
  copied: boolean;
  onCopy: () => void;
  onDownload: () => void;
  tagClassFor: (tag: string) => string;
}) {
  const canCopy =
    typeof navigator !== "undefined" && !!navigator.clipboard?.writeText;
  return (
    <div className={`run-result${stale ? " stale" : ""}`}>
      {stale && (
        <p className="hint run-stale">Re-rendering… showing the previous memo.</p>
      )}

      {/* Provenance banner — the reason this memo is trustworthy. */}
      <div className="run-consistency">
        <div className="run-cons-tags">
          <span className="tag simulated">Simulated numbers</span>
          <span className="tag estimated">Estimated transfers</span>
          <span className="tag generated">Generated prose</span>
          <span className="tag observed">No LLM in numeric path</span>
        </div>
        <p className="run-cons-note">{brief.note}</p>
      </div>

      {/* Memo meta: title, question, horizon, source + length. */}
      <div className="brief-meta">
        <p className="brief-title">{brief.title}</p>
        <p className="brief-question">&ldquo;{brief.question}&rdquo;</p>
        <div className="brief-meta-tags">
          <span className="run-sub-tag">horizon {brief.horizon_label}</span>
          <span className="run-sub-tag">policy {brief.policy_id}</span>
          <span className="run-sub-tag">rendered from {brief.generated_from}</span>
          <span className="run-sub-tag">{brief.word_count.toLocaleString()} words</span>
        </div>
      </div>

      {/* Provenance key printed at the top of the memo (SPEC §34). */}
      {brief.tag_legend.length > 0 && (
        <div className="brief-legend">
          <span className="brief-legend-label">Provenance key</span>
          <ul className="brief-legend-list">
            {brief.tag_legend.map((e, i) => (
              <li key={e.tag ?? i} className="brief-legend-item">
                <span className={`tag ${tagClassFor(e.tag)}`}>{e.tag}</span>
                <span className="brief-legend-meaning">{e.meaning}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Export toolbar. */}
      <div className="brief-toolbar">
        <button
          type="button"
          className="btn"
          onClick={onCopy}
          disabled={!canCopy}
          title={canCopy ? "Copy the Markdown memo" : "Clipboard unavailable"}
        >
          {copied ? "Copied ✓" : "Copy Markdown"}
        </button>
        <button type="button" className="btn" onClick={onDownload}>
          Download .md
        </button>
        <span className="brief-toolbar-hint">
          The memo is shown exactly as the backend produced it — verbatim, so no
          number or provenance tag can be altered here.
        </span>
      </div>

      {/* The self-contained Markdown memo, rendered faithfully (verbatim source). */}
      <h3 className="run-sub">
        The memo
        <span className="run-sub-tag">Markdown · self-contained · verbatim</span>
      </h3>
      <pre className="brief-memo" aria-label="Minister's Brief Markdown memo">
        {brief.markdown}
      </pre>
    </div>
  );
}
