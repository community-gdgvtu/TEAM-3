"""Policy optimiser endpoint (ROADMAP stretch, SPEC §22).

``POST /optimise`` takes an objective + constraints, grid-searches candidate
interventions, simulates each, and returns the feasible Pareto frontier plus
representative recommendations (cheapest / most equitable / largest emissions
reduction / best balanced). Outcome metrics are Simulated; the budget cost proxy
is an Estimated documented constant. No LLM on the numeric path (SPEC §34).
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from ..optimiser import OptimiserResult, optimise_policy
from ..simulation.shocks import Shocks

router = APIRouter(prefix="/optimise", tags=["optimise"])


class OptimiseRequest(BaseModel):
    """Input to ``POST /optimise`` (SPEC §22)."""

    objective: dict = Field(
        default_factory=dict,
        description="Objective targets, e.g. {'reduce_transport_emissions_pct': 20}.",
    )
    constraints: dict = Field(
        default_factory=dict,
        description="Constraints, e.g. {'max_average_commute_increase_pct': 5, "
        "'max_low_income_burden_increase_pct': 2, 'max_budget': 100000000}.",
    )
    shocks: Shocks | None = Field(default=None, description="Optional exogenous stressors.")


@router.post("", response_model=OptimiserResult, summary="Objective → Pareto policy set")
def optimise(req: OptimiseRequest) -> OptimiserResult:
    """Search the candidate grid and return the Pareto frontier."""
    return optimise_policy(req.objective, req.constraints, shocks=req.shocks)
