"use client";

/**
 * The sell: every layer of the twin, grouped by what it's for, before the
 * "Advanced" disclosure buries them behind a click. Order mirrors the real
 * pipeline a policy travels through (compile → project → contest → stress-test
 * → zoom in → prove), the same order DemoTour narrates — so the eyebrow
 * numbers here are a real sequence, not decoration.
 *
 * Clicking a card (or one of its panel pills) expands the Advanced twin and
 * asks PanelTabs to switch straight to that tab, via the same pub/sub DemoTour
 * uses (lib/demo.ts) — no prop-drilling into a component that mounts later.
 */

import { requestDemoTab, requestOpenAdvanced, type DemoTab } from "../../lib/demo";
import Reveal from "../Reveal";

interface Feature {
  key: DemoTab;
  label: string;
}

interface Category {
  stage: string;
  title: string;
  blurb: string;
  accent: "cyan" | "amber";
  features: Feature[];
}

const CATEGORIES: Category[] = [
  {
    stage: "01",
    title: "Compile & project",
    blurb:
      "Turn prose into a structured policy, then run it forward: land use, " +
      "travel demand and the built city over a ten-year horizon.",
    accent: "cyan",
    features: [
      { key: "world", label: "World" },
      { key: "dynamics", label: "Dynamics" },
      { key: "spatial", label: "Spatial" },
      { key: "timeseries", label: "Time-series" },
      { key: "run", label: "Run" },
    ],
  },
  {
    stage: "02",
    title: "Put it to the room",
    blurb:
      "Five adversarial personas, the public, the press and a live presser " +
      "react — with citations, not vibes.",
    accent: "amber",
    features: [
      { key: "parliament", label: "Parliament" },
      { key: "public", label: "Public" },
      { key: "press", label: "Press" },
      { key: "presser", label: "Presser" },
      { key: "institutions", label: "Institutions" },
      { key: "redteam", label: "Red Team" },
    ],
  },
  {
    stage: "03",
    title: "Stress-test it",
    blurb:
      "Compare against alternatives, rank by robustness, and probe every " +
      "edge: sensitivity, uncertainty, backtests, second-order effects.",
    accent: "cyan",
    features: [
      { key: "compare", label: "Compare" },
      { key: "grand", label: "Grand A/B/C/D" },
      { key: "sensitivity", label: "Sensitivity" },
      { key: "uncertainty", label: "Uncertainty" },
      { key: "robustness", label: "Robustness" },
      { key: "backtest", label: "Backtest" },
      { key: "ensemble", label: "Ensemble" },
      { key: "optimiser", label: "Optimiser" },
      { key: "stress", label: "Stress" },
      { key: "diffusion", label: "Diffusion" },
      { key: "sdg", label: "SDG" },
      { key: "economy", label: "Economy" },
      { key: "microsim", label: "Microsim" },
    ],
  },
  {
    stage: "04",
    title: "Zoom to one life",
    blurb:
      "Drill into a single household or firm, and check the policy against " +
      "real-world precedent.",
    accent: "amber",
    features: [
      { key: "citizen", label: "Citizen" },
      { key: "business", label: "Business" },
      { key: "analogue", label: "Analogue" },
    ],
  },
  {
    stage: "05",
    title: "Prove it",
    blurb:
      "The transparency layer: sources, assumptions, a reproducibility " +
      "receipt, and the one fused answer to “what happens if we do this?”.",
    accent: "cyan",
    features: [
      { key: "registry", label: "Registry" },
      { key: "reproduce", label: "Reproduce" },
      { key: "datafabric", label: "Data Fabric" },
      { key: "assumptions", label: "Assumptions" },
      { key: "brief", label: "Brief" },
      { key: "northstar", label: "North-Star" },
    ],
  },
];

const TOTAL_FEATURES = CATEGORIES.reduce((n, c) => n + c.features.length, 0);

function openTab(tab: DemoTab) {
  requestOpenAdvanced();
  requestDemoTab(tab);
  // Give the disclosure a tick to mount PanelTabs before scrolling to it.
  requestAnimationFrame(() => {
    document.getElementById("advanced")?.scrollIntoView({ block: "start" });
  });
}

export default function FeatureShowcase() {
  return (
    <section className="showcase" aria-labelledby="showcase-title">
      <div className="showcase-head">
        <div>
          <p className="eyebrow">The full instrument</p>
          <h2 id="showcase-title" className="showcase-title">
            One policy, {TOTAL_FEATURES} ways to test it
          </h2>
          <p className="lede showcase-lede">
            Meridia above is the fast, in-browser read. Everything below runs
            the real backend engine — five stages, {CATEGORIES.length} groups,{" "}
            {TOTAL_FEATURES} panels. Click any card to open it.
          </p>
        </div>
        <IsometricStack />
      </div>

      <ol className="showcase-grid">
        {CATEGORIES.map((c, i) => (
          <li key={c.stage}>
            <Reveal className={`showcase-card accent-${c.accent}`} delay={i * 70}>
              <button
                type="button"
                className="showcase-card-hit"
                onClick={() => openTab(c.features[0].key)}
                aria-label={`Open ${c.title}`}
              >
                <span className="showcase-stage">{c.stage}</span>
                <h3 className="showcase-card-title">{c.title}</h3>
                <p className="showcase-blurb">{c.blurb}</p>
              </button>
              <div className="showcase-pills">
                {c.features.map((f) => (
                  <button
                    key={f.key}
                    type="button"
                    className="tag showcase-pill"
                    onClick={() => openTab(f.key)}
                  >
                    {f.label}
                  </button>
                ))}
              </div>
            </Reveal>
          </li>
        ))}
      </ol>
    </section>
  );
}

/** A small isometric instrument-stack: City → Model → Decision. Pure CSS. */
function IsometricStack() {
  return (
    <div className="iso-scene" aria-hidden>
      <div className="iso-stage">
        <div className="iso-slab iso-slab-1">
          <span>Decision</span>
        </div>
        <div className="iso-slab iso-slab-2">
          <span>Model</span>
        </div>
        <div className="iso-slab iso-slab-3">
          <span>City</span>
        </div>
      </div>
    </div>
  );
}
