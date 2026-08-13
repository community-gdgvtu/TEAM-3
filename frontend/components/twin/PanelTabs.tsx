"use client";

/**
 * Lower deck of the main screen (SPEC §27): the [Parliament] [Public] [Press]
 * [Red Team] tab bar and the panel it selects.
 *
 * All four panels stay mounted (toggled with `hidden`) so a debate, opinion run,
 * press batch or risk register survives switching tabs — the demo can flip
 * between them without re-fetching. A shared "no policy yet" hint sits above the
 * bar until the compiler publishes a DSL (each panel also guards itself).
 */

import { useState } from "react";

import ParliamentPanel from "./ParliamentPanel";
import PublicReactionPanel from "./PublicReactionPanel";
import PressFeedPanel from "./PressFeedPanel";
import FailureModesPanel from "./FailureModesPanel";
import SdgPanel from "./SdgPanel";
import DiffusionPanel from "./DiffusionPanel";
import BacktestPanel from "./BacktestPanel";
import { useTwin } from "./TwinStore";

type TabKey =
  | "parliament"
  | "public"
  | "press"
  | "redteam"
  | "sdg"
  | "diffusion"
  | "backtest";

const TABS: Array<{ key: TabKey; label: string }> = [
  { key: "parliament", label: "Parliament" },
  { key: "public", label: "Public" },
  { key: "press", label: "Press" },
  { key: "redteam", label: "Red Team" },
  { key: "sdg", label: "SDG" },
  { key: "diffusion", label: "Diffusion" },
  { key: "backtest", label: "Backtest" },
];

export default function PanelTabs() {
  const { policy } = useTwin();
  const [active, setActive] = useState<TabKey>("parliament");

  return (
    <div className="panel-tabs">
      <div className="tabbar" role="tablist" aria-label="Analysis panels">
        {TABS.map((t) => (
          <button
            key={t.key}
            type="button"
            role="tab"
            aria-selected={active === t.key}
            className={`tab${active === t.key ? " active" : ""}`}
            onClick={() => setActive(t.key)}
          >
            {t.label}
          </button>
        ))}
        {!policy && (
          <span className="tabbar-hint">
            Compile a policy to activate (Backtest runs without one)
          </span>
        )}
      </div>

      <div className="tab-panels">
        <div role="tabpanel" hidden={active !== "parliament"}>
          <ParliamentPanel />
        </div>
        <div role="tabpanel" hidden={active !== "public"}>
          <PublicReactionPanel />
        </div>
        <div role="tabpanel" hidden={active !== "press"}>
          <PressFeedPanel />
        </div>
        <div role="tabpanel" hidden={active !== "redteam"}>
          <FailureModesPanel />
        </div>
        <div role="tabpanel" hidden={active !== "sdg"}>
          <SdgPanel />
        </div>
        <div role="tabpanel" hidden={active !== "diffusion"}>
          <DiffusionPanel />
        </div>
        <div role="tabpanel" hidden={active !== "backtest"}>
          <BacktestPanel />
        </div>
      </div>
    </div>
  );
}
