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

import { useEffect, useState } from "react";

import { subscribeDemoTab } from "../../lib/demo";
import NorthStarPanel from "./NorthStarPanel";
import RunPanel from "./RunPanel";
import WorldPanel from "./WorldPanel";
import CitizenPanel from "./CitizenPanel";
import BusinessPanel from "./BusinessPanel";
import ParliamentPanel from "./ParliamentPanel";
import PublicReactionPanel from "./PublicReactionPanel";
import PressFeedPanel from "./PressFeedPanel";
import FailureModesPanel from "./FailureModesPanel";
import SdgPanel from "./SdgPanel";
import DiffusionPanel from "./DiffusionPanel";
import BacktestPanel from "./BacktestPanel";
import EnsemblePanel from "./EnsemblePanel";
import RegistryPanel from "./RegistryPanel";
import InstitutionsPanel from "./InstitutionsPanel";
import PressConferencePanel from "./PressConferencePanel";
import ComparePanel from "./ComparePanel";
import GrandComparePanel from "./GrandComparePanel";
import UncertaintyPanel from "./UncertaintyPanel";
import SensitivityPanel from "./SensitivityPanel";
import OptimiserPanel from "./OptimiserPanel";
import EconomyPanel from "./EconomyPanel";
import DynamicsPanel from "./DynamicsPanel";
import MicrosimPanel from "./MicrosimPanel";
import SpatialPanel from "./SpatialPanel";
import StressPanel from "./StressPanel";
import AnaloguePanel from "./AnaloguePanel";
import TimeseriesPanel from "./TimeseriesPanel";
import ReproducePanel from "./ReproducePanel";
import DataFabricPanel from "./DataFabricPanel";
import AssumptionsPanel from "./AssumptionsPanel";
import { useTwin } from "./TwinStore";

type TabKey =
  | "northstar"
  | "run"
  | "world"
  | "citizen"
  | "business"
  | "parliament"
  | "public"
  | "press"
  | "presser"
  | "redteam"
  | "compare"
  | "grand"
  | "sdg"
  | "diffusion"
  | "ensemble"
  | "uncertainty"
  | "sensitivity"
  | "optimiser"
  | "economy"
  | "dynamics"
  | "microsim"
  | "spatial"
  | "stress"
  | "analogue"
  | "timeseries"
  | "institutions"
  | "backtest"
  | "registry"
  | "reproduce"
  | "datafabric"
  | "assumptions";

const TABS: Array<{ key: TabKey; label: string }> = [
  { key: "northstar", label: "North-Star" },
  { key: "run", label: "Run" },
  { key: "world", label: "World" },
  { key: "citizen", label: "Citizen" },
  { key: "business", label: "Business" },
  { key: "parliament", label: "Parliament" },
  { key: "public", label: "Public" },
  { key: "press", label: "Press" },
  { key: "presser", label: "Presser" },
  { key: "redteam", label: "Red Team" },
  { key: "compare", label: "Compare" },
  { key: "grand", label: "Grand A/B/C/D" },
  { key: "sdg", label: "SDG" },
  { key: "diffusion", label: "Diffusion" },
  { key: "ensemble", label: "Ensemble" },
  { key: "uncertainty", label: "Uncertainty" },
  { key: "sensitivity", label: "Sensitivity" },
  { key: "optimiser", label: "Optimiser" },
  { key: "economy", label: "Economy" },
  { key: "dynamics", label: "Dynamics" },
  { key: "microsim", label: "Microsim" },
  { key: "spatial", label: "Spatial" },
  { key: "stress", label: "Stress" },
  { key: "analogue", label: "Analogue" },
  { key: "timeseries", label: "Time-series" },
  { key: "institutions", label: "Institutions" },
  { key: "backtest", label: "Backtest" },
  { key: "registry", label: "Registry" },
  { key: "reproduce", label: "Reproduce" },
  { key: "datafabric", label: "Data Fabric" },
  { key: "assumptions", label: "Assumptions" },
];

export default function PanelTabs() {
  const { policy } = useTwin();
  const [active, setActive] = useState<TabKey>("parliament");

  // Let the guided demo drive the tab bar (its keys are a subset of TabKey).
  useEffect(() => subscribeDemoTab((tab) => setActive(tab)), []);

  return (
    <div className="panel-tabs" data-tour="tabs">
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
            Compile a policy to activate (Backtest, Registry &amp; Optimiser run without one)
          </span>
        )}
      </div>

      <div className="tab-panels">
        <div role="tabpanel" hidden={active !== "northstar"}>
          <NorthStarPanel />
        </div>
        <div role="tabpanel" hidden={active !== "run"}>
          <RunPanel />
        </div>
        <div role="tabpanel" hidden={active !== "world"}>
          <WorldPanel />
        </div>
        <div role="tabpanel" hidden={active !== "citizen"}>
          <CitizenPanel />
        </div>
        <div role="tabpanel" hidden={active !== "business"}>
          <BusinessPanel />
        </div>
        <div role="tabpanel" hidden={active !== "parliament"}>
          <ParliamentPanel />
        </div>
        <div role="tabpanel" hidden={active !== "public"}>
          <PublicReactionPanel />
        </div>
        <div role="tabpanel" hidden={active !== "press"}>
          <PressFeedPanel />
        </div>
        <div role="tabpanel" hidden={active !== "presser"}>
          <PressConferencePanel />
        </div>
        <div role="tabpanel" hidden={active !== "redteam"}>
          <FailureModesPanel />
        </div>
        <div role="tabpanel" hidden={active !== "compare"}>
          <ComparePanel />
        </div>
        <div role="tabpanel" hidden={active !== "grand"}>
          <GrandComparePanel />
        </div>
        <div role="tabpanel" hidden={active !== "sdg"}>
          <SdgPanel />
        </div>
        <div role="tabpanel" hidden={active !== "diffusion"}>
          <DiffusionPanel />
        </div>
        <div role="tabpanel" hidden={active !== "ensemble"}>
          <EnsemblePanel />
        </div>
        <div role="tabpanel" hidden={active !== "uncertainty"}>
          <UncertaintyPanel />
        </div>
        <div role="tabpanel" hidden={active !== "sensitivity"}>
          <SensitivityPanel />
        </div>
        <div role="tabpanel" hidden={active !== "optimiser"}>
          <OptimiserPanel />
        </div>
        <div role="tabpanel" hidden={active !== "economy"}>
          <EconomyPanel />
        </div>
        <div role="tabpanel" hidden={active !== "dynamics"}>
          <DynamicsPanel />
        </div>
        <div role="tabpanel" hidden={active !== "microsim"}>
          <MicrosimPanel />
        </div>
        <div role="tabpanel" hidden={active !== "spatial"}>
          <SpatialPanel />
        </div>
        <div role="tabpanel" hidden={active !== "stress"}>
          <StressPanel />
        </div>
        <div role="tabpanel" hidden={active !== "analogue"}>
          <AnaloguePanel />
        </div>
        <div role="tabpanel" hidden={active !== "timeseries"}>
          <TimeseriesPanel />
        </div>
        <div role="tabpanel" hidden={active !== "institutions"}>
          <InstitutionsPanel />
        </div>
        <div role="tabpanel" hidden={active !== "backtest"}>
          <BacktestPanel />
        </div>
        <div role="tabpanel" hidden={active !== "registry"}>
          <RegistryPanel />
        </div>
        <div role="tabpanel" hidden={active !== "reproduce"}>
          <ReproducePanel />
        </div>
        <div role="tabpanel" hidden={active !== "datafabric"}>
          <DataFabricPanel />
        </div>
        <div role="tabpanel" hidden={active !== "assumptions"}>
          <AssumptionsPanel />
        </div>
      </div>
    </div>
  );
}
