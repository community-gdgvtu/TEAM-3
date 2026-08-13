"use client";

/**
 * Ambient AI-persona card for the default (no-backend-required) screen: the
 * policy's sponsor, in character, stating her intention for the chosen
 * scenario and reading off the live effects as you drag the scrubber — plus
 * one adversarial line so it isn't just marketing copy.
 *
 * Deliberately client-side and deterministic (`lib/cityModel.ts`), same as the
 * rest of the simple view: it updates every frame the scrubber moves with no
 * network round-trip, and works with the backend down. It is Generated prose
 * over Simulated numbers — never the other way round (SPEC §34). For an
 * open-ended, LLM-answered follow-up question to any of the five Parliament
 * personas (grounded in the backend's own simulation), see "Ask a persona" in
 * Advanced → Parliament.
 */

import { SPONSOR, politicianStatement } from "../../lib/cityModel";
import type { CityState, Scenario } from "../../lib/cityModel";

function initials(name: string): string {
  return name
    .split(" ")
    .map((w) => w[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();
}

export default function PoliticianCard({
  year,
  scenario,
  state,
  reference,
}: {
  year: number;
  scenario: Scenario;
  state: CityState;
  reference: CityState;
}) {
  const s = politicianStatement(year, scenario, state, reference);

  return (
    <div className={`politician-card tone-${s.tone}`}>
      <div className="politician-head">
        <span className="politician-avatar" aria-hidden>
          {initials(SPONSOR.name)}
        </span>
        <div className="politician-id">
          <strong className="politician-name">{SPONSOR.name}</strong>
          <span className="politician-title">{SPONSOR.title}</span>
        </div>
        <span
          className="tag generated"
          title="Deterministic template reading the Simulated numbers below — no language model produced this text."
        >
          Generated
        </span>
      </div>

      <p className="politician-quote">&ldquo;{s.intention}&rdquo;</p>

      <ul className="politician-effects">
        {s.effects.map((e, i) => (
          <li key={i}>{e}</li>
        ))}
      </ul>

      <p className="politician-rebuttal">
        <span className="politician-rebuttal-label">Opposition line</span>
        {s.rebuttal}
      </p>
    </div>
  );
}
