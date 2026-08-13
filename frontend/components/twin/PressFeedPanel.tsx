"use client";

/**
 * Simulated press feed (SPEC §15/§27): archetype media coverage from
 * `POST /media` at Month 5 and Year 2. Coverage is generated from generic outlet
 * *archetypes* (public broadcaster, business press, local paper, tabloid,
 * environmental, industry) — never real outlets or bylines.
 *
 * Provenance (SPEC §34): every card carries the mandatory SIMULATED banner, is
 * tagged Generated, and cites only the event-ledger entries / outcome metrics it
 * was built from — narratives never invent quantitative events. The disclaimer is
 * shown once up top and stamped on every card so nothing can be mistaken for a
 * real article.
 */

import { useEffect, useState } from "react";

import { runMedia } from "../../lib/api";
import type {
  Headline,
  MediaArchetype,
  MediaResponse,
  MediaScenario,
} from "../../lib/api";
import { useTwin } from "./TwinStore";

const ARCHETYPE_LABEL: Record<MediaArchetype, string> = {
  public_broadcaster: "Public broadcaster",
  business_press: "Business press",
  local_news: "Local news",
  tabloid: "Tabloid",
  environmental: "Environmental",
  industry: "Industry",
};

type Status = "idle" | "loading" | "ready" | "error";

export default function PressFeedPanel() {
  const { policy } = useTwin();
  const [status, setStatus] = useState<Status>("idle");
  const [media, setMedia] = useState<MediaResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setMedia(null);
    setStatus("idle");
    setError(null);
  }, [policy]);

  async function generate() {
    if (!policy) return;
    setStatus("loading");
    setError(null);
    try {
      const m = await runMedia(policy);
      setMedia(m);
      setStatus("ready");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Media generation failed");
      setStatus("error");
    }
  }

  return (
    <section className="card press">
      <div className="dashboard-head">
        <h2>Simulated press</h2>
        <span className="dashboard-sub">
          Archetype coverage · prose Generated, every cited figure Simulated
        </span>
      </div>

      {!policy ? (
        <div className="waiting">
          <span className="tag muted">No policy yet</span>
          <p>Compile a policy above to generate how the press might cover it.</p>
        </div>
      ) : (
        <>
          <div className="policy-actions" style={{ marginTop: 0 }}>
            <button
              type="button"
              className="btn primary"
              onClick={generate}
              disabled={status === "loading"}
            >
              {status === "loading"
                ? "Generating…"
                : media
                  ? "Regenerate coverage"
                  : "Generate press coverage"}
            </button>
            {media && (
              <span className="tag muted">
                {media.method === "llm" ? "LLM prose" : "Template prose"}
              </span>
            )}
          </div>

          {status === "error" && (
            <p className="hint error-text">Couldn&rsquo;t generate: {error}</p>
          )}

          {media && status === "ready" && (
            <div className="press-body">
              <div className="press-disclaimer">
                <span className="tag simulated">SIMULATED</span>
                <span>{media.disclaimer}</span>
              </div>

              {media.scenarios.map((s) => (
                <ScenarioBlock key={s.label} scenario={s} />
              ))}

              <p className="hint press-note">{media.note}</p>
            </div>
          )}
        </>
      )}
    </section>
  );
}

function ScenarioBlock({ scenario }: { scenario: MediaScenario }) {
  return (
    <div className="press-scenario">
      <div className="press-scenario-head">
        <span className="press-horizon">{scenario.label}</span>
        <span className="press-count">
          {scenario.headlines.length} outlet
          {scenario.headlines.length === 1 ? "" : "s"}
        </span>
      </div>
      <div className="press-grid">
        {scenario.headlines.map((h, i) => (
          <HeadlineCard key={`${h.archetype}-${i}`} h={h} />
        ))}
      </div>
    </div>
  );
}

function HeadlineCard({ h }: { h: Headline }) {
  const sentiment =
    h.sentiment === "positive"
      ? "pos"
      : h.sentiment === "critical"
        ? "neg"
        : "mixed";
  return (
    <article className="press-card" title={h.label}>
      <div className="press-card-head">
        <span className="press-outlet">{h.outlet_label}</span>
        <span className="press-arch">
          {ARCHETYPE_LABEL[h.archetype] ?? h.archetype}
        </span>
      </div>

      <h3 className="press-headline">{h.headline}</h3>
      <p className="press-standfirst">{h.standfirst}</p>

      <div className="press-meta">
        <span className={`sentiment-chip ${sentiment}`}>{h.sentiment}</span>
        <span className="press-angle">{h.angle}</span>
      </div>

      {h.cited_refs.length > 0 && (
        <div className="press-refs">
          <span className="press-refs-label">built from</span>
          {h.cited_refs.map((r) => (
            <span key={r} className="citation">
              <span className="citation-detail">{r}</span>
            </span>
          ))}
        </div>
      )}

      <div className="press-stamp">
        <span className="tag simulated">SIMULATED</span>
      </div>
    </article>
  );
}
