"""Citizen View — per-agent "follow a single household" drill-down (SPEC §17/§31).

Every other layer *aggregates* the synthetic population (microsim → income
deciles, world → distributions, opinion → cohorts). SPEC §17's Citizen View and
the §31 ``Agent State`` core data structure ask the opposite question: pick **one**
synthetic household and show how the policy changes *their* daily life over the
Time Machine — commute, transport cost and support, before vs each horizon, with
the "why". This layer answers exactly that, reusing the same deterministic
mode-choice + opinion + staged-adaptation models as ``/simulate`` and ``/public``
so a citizen's numbers can never disagree with the aggregates beside them.
"""

from .service import build_citizen_view, sample_citizens
from .schema import (
    AgentState,
    CitizenProfile,
    CitizenSnapshot,
    CitizenView,
    CitizenSample,
)

__all__ = [
    "build_citizen_view",
    "sample_citizens",
    "AgentState",
    "CitizenProfile",
    "CitizenSnapshot",
    "CitizenView",
    "CitizenSample",
]
