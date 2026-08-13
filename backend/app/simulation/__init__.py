"""Policy simulation (World B) package — ROADMAP M3, SPEC §7.5/§7.7.

Deterministic agent-based mode-choice + traffic model that applies a compiled
Policy DSL (a cordon charge, pedestrianisation, transit reinvestment) to the
synthetic population and re-aggregates the same headline metric families as the
baseline. No LLM touches the numeric path (SPEC §34).
"""

from .levers import DEFAULT_SIM_PARAMS, PolicyLevers, SimParams, derive_levers
from .model import choose_mode_policy, compute_world_b
from .schema import BehaviouralRule, WorldBMetrics

__all__ = [
    "derive_levers",
    "PolicyLevers",
    "SimParams",
    "DEFAULT_SIM_PARAMS",
    "choose_mode_policy",
    "compute_world_b",
    "WorldBMetrics",
    "BehaviouralRule",
]
