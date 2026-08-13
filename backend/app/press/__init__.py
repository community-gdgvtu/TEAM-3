"""Press Conference simulation (SPEC §16).

After a policy is announced, a government spokesperson faces a room of archetype
journalists. This package builds that scene *from the model's own numbers*: an
opening statement and a set of pointed, adversarial questions — each grounded in
a specific Δ metric, event-ledger entry or opinion figure — with a spokesperson
answer that cites the same figures. Numbers come only from the deterministic
simulation; an LLM may polish the *prose* (with a template fallback) but never
invents a figure (SPEC §16/§34).
"""

from .conference import build_press_conference, run_press_conference
from .schema import (
    PressAnswer,
    PressConference,
    PressExchange,
    PressQuestion,
    ReporterArchetype,
)

__all__ = [
    "build_press_conference",
    "run_press_conference",
    "PressConference",
    "PressExchange",
    "PressQuestion",
    "PressAnswer",
    "ReporterArchetype",
]
