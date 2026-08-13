"use client";

/**
 * Everything the simple view deliberately leaves out, behind one disclosure.
 *
 * The default screen is the 3D city and the ten-year scrubber. The full policy
 * twin — the LLM policy compiler, the backend simulation with uncertainty
 * bands, the evidence drawer, and the parliament / public / press / red-team /
 * optimiser panels — is unchanged and lives here. Nothing is mounted until the
 * section is opened, so the simple view stays fast and works with the backend
 * down.
 */

import { useEffect, useState } from "react";

import PolicyCompiler from "../../app/PolicyCompiler";
import HealthStatus from "../../app/HealthStatus";
import { subscribeOpenAdvanced } from "../../lib/demo";
import DemoTour from "./DemoTour";
import PanelTabs from "./PanelTabs";
import TwinWorkspace from "./TwinWorkspace";

export default function AdvancedTwin() {
  const [open, setOpen] = useState(false);

  // Let a feature card (or the guided demo) expand this disclosure directly
  // instead of requiring a manual click first.
  useEffect(() => subscribeOpenAdvanced(() => setOpen(true)), []);

  return (
    <section id="advanced" className="advanced">
      <button
        type="button"
        className="advanced-toggle"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
      >
        <span className="advanced-caret" aria-hidden>
          {open ? "▾" : "▸"}
        </span>
        <span>
          <strong>Advanced — the full policy twin</strong>
          <span className="advanced-sub">
            Write a policy in plain language, run the backend simulation engine
            with uncertainty bands, then take it through parliament, the public,
            the press and the red team. Needs the FastAPI backend running.
          </span>
        </span>
      </button>

      {open && (
        <div className="advanced-body">
          <PolicyCompiler />
          <TwinWorkspace />
          <PanelTabs />
          <HealthStatus />
          <DemoTour />
        </div>
      )}
    </section>
  );
}
