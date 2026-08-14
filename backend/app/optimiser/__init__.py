"""Policy optimiser stub (ROADMAP stretch, SPEC §22).

Objective → search candidate policy grid → simulate → Pareto frontier →
representative recommendations. Outcome metrics are Simulated; the budget cost
proxy is an Estimated documented constant. No LLM on the numeric path (SPEC §34).
"""

from __future__ import annotations

from .schema import (
    Candidate,
    CandidateConfig,
    CandidateMetrics,
    OptimiserResult,
    Recommendations,
)
from .search import COST_MODEL, OBJECTIVE_AXES, optimise_policy

__all__ = [
    "COST_MODEL",
    "OBJECTIVE_AXES",
    "Candidate",
    "CandidateConfig",
    "CandidateMetrics",
    "OptimiserResult",
    "Recommendations",
    "optimise_policy",
]
