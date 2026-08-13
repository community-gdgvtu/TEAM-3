"""Stress-testing layer (SPEC §20).

Separates a policy's *own* effect from exogenous scenario assumptions ("shocks")
and asks the SPEC §20 question directly: **does the policy still work under a
recession, a fuel-price spike, faster population growth …, or does it fail?**

Every shock is a *transparent, named scenario assumption* (SPEC §20: "Shocks are
scenario assumptions, not secretly random events") expressed in terms of the
existing deterministic :class:`~app.simulation.shocks.Shocks` knobs. No LLM is
involved in any number (SPEC §34); shock magnitudes are Estimated inputs and the
resulting policy deltas are Simulated.
"""

from .catalogue import SHOCK_CATALOGUE, ShockScenario, get_scenario
from .model import run_stress_test
from .schema import (
    MetricStress,
    ScenarioResult,
    StressReport,
    StressRobustness,
)

__all__ = [
    "SHOCK_CATALOGUE",
    "ShockScenario",
    "get_scenario",
    "run_stress_test",
    "MetricStress",
    "ScenarioResult",
    "StressReport",
    "StressRobustness",
]
