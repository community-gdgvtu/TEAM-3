"""Simulated media generator package (ROADMAP M6, SPEC §15).

Generates clearly-labelled SIMULATED media coverage from archetypes (never real
outlets), built strictly from the event ledger, outcome metrics and opinion
state. Generated prose over Simulated figures; no invented events, no real
bylines (SPEC §15/§34).
"""

from .generator import build_media, run_media
from .schema import (
    SIMULATED_LABEL,
    Headline,
    MediaArchetype,
    MediaResponse,
    MediaScenario,
)

__all__ = [
    "build_media",
    "run_media",
    "Headline",
    "MediaArchetype",
    "MediaResponse",
    "MediaScenario",
    "SIMULATED_LABEL",
]
