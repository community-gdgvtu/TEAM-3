"""Scenario orchestrator package (SPEC §28/§29).

Composes the engine's deterministic layers into the single killer-demo narrative
exposed by ``POST /run``. Adds no new numeric model — it reuses the existing
per-layer services so every section shares one compiled policy and one
simulation (SPEC §34 cross-layer consistency).
"""

from .schema import (
    HeadlineMetric,
    NarrativeBeat,
    ProposedAmendment,
    RunRequest,
    RunResponse,
)
from .service import run_scenario

__all__ = [
    "run_scenario",
    "RunRequest",
    "RunResponse",
    "HeadlineMetric",
    "NarrativeBeat",
    "ProposedAmendment",
]
