"use client";

/**
 * Lower deck of the main screen (SPEC §27): the analysis tab bar and the panel
 * it selects.
 *
 * All panels stay mounted (toggled with `hidden`) so a debate, opinion run,
 * press batch or risk register survives switching tabs — the demo can flip
 * between them without re-fetching. A shared "no policy yet" hint sits above the
 * bar until the compiler publishes a DSL (each panel also guards itself).
 *
 * The bar implements the WAI-ARIA Tabs pattern (APG): a single tab stop with a
 * roving `tabIndex`, ArrowLeft/ArrowRight/Home/End keyboard navigation with
 * automatic activation, and `aria-controls`/`aria-labelledby` wiring each tab to
 * its panel. With 31 panels a flat bar is hard to scan, so a filter box narrows
 * the visible tabs by label (the active tab always stays visible so a filtered
 * view can never orphan the panel on screen). Keyboard navigation traverses only
 * the currently-visible tabs.
 */

import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ComponentType,
  type KeyboardEvent as ReactKeyboardEvent,
} from "react";

import { subscribeDemoTab } from "../../lib/demo";
import NorthStarPanel from "./NorthStarPanel";
import BriefPanel from "./BriefPanel";
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
import CapabilitiesPanel from "./CapabilitiesPanel";
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
import RobustnessPanel from "./RobustnessPanel";
import AnaloguePanel from "./AnaloguePanel";
import TimeseriesPanel from "./TimeseriesPanel";
import ReproducePanel from "./ReproducePanel";
import DataFabricPanel from "./DataFabricPanel";
import AssumptionsPanel from "./AssumptionsPanel";
import { useTwin } from "./TwinStore";

type TabKey =
  | "northstar"
  | "brief"
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
  | "robustness"
  | "analogue"
  | "timeseries"
  | "institutions"
  | "backtest"
  | "registry"
  | "capabilities"
  | "reproduce"
  | "datafabric"
  | "assumptions";

const TABS: Array<{ key: TabKey; label: string; Panel: ComponentType }> = [
  { key: "northstar", label: "North-Star", Panel: NorthStarPanel },
  { key: "brief", label: "Brief", Panel: BriefPanel },
  { key: "run", label: "Run", Panel: RunPanel },
  { key: "world", label: "World", Panel: WorldPanel },
  { key: "citizen", label: "Citizen", Panel: CitizenPanel },
  { key: "business", label: "Business", Panel: BusinessPanel },
  { key: "parliament", label: "Parliament", Panel: ParliamentPanel },
  { key: "public", label: "Public", Panel: PublicReactionPanel },
  { key: "press", label: "Press", Panel: PressFeedPanel },
  { key: "presser", label: "Presser", Panel: PressConferencePanel },
  { key: "redteam", label: "Red Team", Panel: FailureModesPanel },
  { key: "compare", label: "Compare", Panel: ComparePanel },
  { key: "grand", label: "Grand A/B/C/D", Panel: GrandComparePanel },
  { key: "sdg", label: "SDG", Panel: SdgPanel },
  { key: "diffusion", label: "Diffusion", Panel: DiffusionPanel },
  { key: "ensemble", label: "Ensemble", Panel: EnsemblePanel },
  { key: "uncertainty", label: "Uncertainty", Panel: UncertaintyPanel },
  { key: "sensitivity", label: "Sensitivity", Panel: SensitivityPanel },
  { key: "optimiser", label: "Optimiser", Panel: OptimiserPanel },
  { key: "economy", label: "Economy", Panel: EconomyPanel },
  { key: "dynamics", label: "Dynamics", Panel: DynamicsPanel },
  { key: "microsim", label: "Microsim", Panel: MicrosimPanel },
  { key: "spatial", label: "Spatial", Panel: SpatialPanel },
  { key: "stress", label: "Stress", Panel: StressPanel },
  { key: "robustness", label: "Robustness", Panel: RobustnessPanel },
  { key: "analogue", label: "Analogue", Panel: AnaloguePanel },
  { key: "timeseries", label: "Time-series", Panel: TimeseriesPanel },
  { key: "institutions", label: "Institutions", Panel: InstitutionsPanel },
  { key: "backtest", label: "Backtest", Panel: BacktestPanel },
  { key: "registry", label: "Registry", Panel: RegistryPanel },
  { key: "capabilities", label: "Capabilities", Panel: CapabilitiesPanel },
  { key: "reproduce", label: "Reproduce", Panel: ReproducePanel },
  { key: "datafabric", label: "Data Fabric", Panel: DataFabricPanel },
  { key: "assumptions", label: "Assumptions", Panel: AssumptionsPanel },
];

const tabId = (key: TabKey) => `tab-${key}`;
const panelId = (key: TabKey) => `panel-${key}`;

export default function PanelTabs() {
  const { policy } = useTwin();
  const [active, setActive] = useState<TabKey>("parliament");
  const [filter, setFilter] = useState("");
  const tabRefs = useRef<Partial<Record<TabKey, HTMLButtonElement | null>>>({});

  // Let the guided demo drive the tab bar (its keys are a subset of TabKey).
  // Clear any filter so the requested tab (and its neighbours) are in view.
  useEffect(
    () =>
      subscribeDemoTab((tab) => {
        setActive(tab);
        setFilter("");
      }),
    [],
  );

  // Tabs currently shown in the bar: those matching the filter, but the active
  // tab is always kept visible so a narrow filter can never orphan the panel.
  const visibleTabs = useMemo(() => {
    const q = filter.trim().toLowerCase();
    if (!q) return TABS;
    return TABS.filter((t) => t.label.toLowerCase().includes(q) || t.key === active);
  }, [filter, active]);

  const focusTab = useCallback((key: TabKey) => {
    setActive(key);
    // Focus after the roving tabIndex updates so the moved-to tab is the tab stop.
    requestAnimationFrame(() => tabRefs.current[key]?.focus());
  }, []);

  const onKeyDown = useCallback(
    (event: ReactKeyboardEvent<HTMLButtonElement>, key: TabKey) => {
      const list = visibleTabs;
      const count = list.length;
      if (count === 0) return;
      const current = list.findIndex((t) => t.key === key);
      const start = current === -1 ? 0 : current;
      let next = -1;
      switch (event.key) {
        case "ArrowRight":
        case "ArrowDown":
          next = (start + 1) % count;
          break;
        case "ArrowLeft":
        case "ArrowUp":
          next = (start - 1 + count) % count;
          break;
        case "Home":
          next = 0;
          break;
        case "End":
          next = count - 1;
          break;
        default:
          return;
      }
      event.preventDefault();
      focusTab(list[next].key);
    },
    [visibleTabs, focusTab],
  );

  return (
    <div className="panel-tabs" data-tour="tabs">
      <div className="tabbar-row">
        <div className="tabbar" role="tablist" aria-label="Analysis panels">
          {visibleTabs.map((t) => {
            const selected = active === t.key;
            return (
              <button
                key={t.key}
                ref={(el) => {
                  tabRefs.current[t.key] = el;
                }}
                type="button"
                role="tab"
                id={tabId(t.key)}
                aria-selected={selected}
                aria-controls={panelId(t.key)}
                tabIndex={selected ? 0 : -1}
                className={`tab${selected ? " active" : ""}`}
                onClick={() => setActive(t.key)}
                onKeyDown={(e) => onKeyDown(e, t.key)}
              >
                {t.label}
              </button>
            );
          })}
          {visibleTabs.length === 0 && (
            <span className="tabbar-hint" role="status">
              No panel matches “{filter.trim()}”.
            </span>
          )}
          {!policy && visibleTabs.length > 0 && (
            <span className="tabbar-hint">
              Compile a policy to activate (Backtest, Registry &amp; Optimiser run without one)
            </span>
          )}
        </div>
        <div className="tab-filter">
          <label className="sr-only" htmlFor="tab-filter-input">
            Filter analysis panels
          </label>
          <input
            id="tab-filter-input"
            type="search"
            className="tab-filter-input"
            placeholder={`Filter ${TABS.length} panels…`}
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            aria-describedby="tab-filter-count"
          />
          <span id="tab-filter-count" className="tab-filter-count">
            {filter.trim()
              ? `${visibleTabs.filter((t) => t.label.toLowerCase().includes(filter.trim().toLowerCase())).length}/${TABS.length}`
              : `${TABS.length}`}
          </span>
        </div>
      </div>

      <div className="tab-panels">
        {TABS.map((t) => {
          const { Panel } = t;
          const selected = active === t.key;
          return (
            <div
              key={t.key}
              role="tabpanel"
              id={panelId(t.key)}
              aria-labelledby={tabId(t.key)}
              tabIndex={selected ? 0 : -1}
              hidden={!selected}
            >
              <Panel />
            </div>
          );
        })}
      </div>
    </div>
  );
}
