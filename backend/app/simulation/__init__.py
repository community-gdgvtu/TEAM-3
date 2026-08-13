"""Policy simulation (World B) package — ROADMAP M3, SPEC §7.5/§7.7.

Deterministic agent-based mode-choice + traffic model that applies a compiled
Policy DSL (a cordon charge, pedestrianisation, transit reinvestment) to the
synthetic population and re-aggregates the same headline metric families as the
baseline. No LLM touches the numeric path (SPEC §34).
"""

from .compare import build_delta
from .events import DEFAULT_THRESHOLDS, EventThresholds, build_event_ledger
from .levers import DEFAULT_SIM_PARAMS, PolicyLevers, SimParams, derive_levers
from .model import choose_mode_policy, compute_world_b
from .schema import (
    BehaviouralRule,
    DeltaTimeSeries,
    EventLedger,
    LedgerEvent,
    WorldBMetrics,
    WorldBTimeSeries,
)
from .shocks import Shocks, apply_shocks
from .timeline import (
    DEFAULT_ADAPTATION,
    AdaptationParams,
    build_world_b_timeline,
)

__all__ = [
    "derive_levers",
    "PolicyLevers",
    "SimParams",
    "DEFAULT_SIM_PARAMS",
    "choose_mode_policy",
    "compute_world_b",
    "WorldBMetrics",
    "WorldBTimeSeries",
    "BehaviouralRule",
    "build_world_b_timeline",
    "AdaptationParams",
    "DEFAULT_ADAPTATION",
    "build_delta",
    "DeltaTimeSeries",
    "Shocks",
    "apply_shocks",
    "build_event_ledger",
    "EventLedger",
    "LedgerEvent",
    "EventThresholds",
    "DEFAULT_THRESHOLDS",
]
