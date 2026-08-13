"""Scenario-presets package (SPEC §3 / §27 / §28).

The discoverable menu of canonical demo policies — natural-language prompt +
live compiler output + ready-to-POST bodies — so the UI and judges can one-click
load a scenario into any downstream endpoint. No numeric model, no LLM (§34).
"""

from .library import build_library, get_scenario, scenario_ids
from .schema import ScenarioCard, ScenarioLibrary

__all__ = [
    "build_library",
    "get_scenario",
    "scenario_ids",
    "ScenarioCard",
    "ScenarioLibrary",
]
