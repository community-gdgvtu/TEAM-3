"""Policy shortlist ranker endpoints (SPEC §21/§22, decision support).

``POST /shortlist`` ranks a caller-supplied set of 2–8 candidate policies
head-to-head; ``GET /shortlist/example`` runs a keyless three-way demo (the same
congestion charge reinvested in buses vs. paid to the general fund vs. a
pedestrianised core) so a judge can see the ranking with no body.

Every outcome number is Simulated by the deterministic model; the composite score
is an explicit, caller-weighted sum. No LLM produces any number (SPEC §34).
"""

from __future__ import annotations

from fastapi import APIRouter

from ..policy.dsl import Intervention, InterventionType, PolicyDSL, RevenueAllocation
from ..shortlist import (
    PolicyEntry,
    ShortlistRequest,
    ShortlistResult,
    rank_shortlist,
)

router = APIRouter(prefix="/shortlist", tags=["shortlist"])


@router.post("", response_model=ShortlistResult, summary="Rank a shortlist of candidate policies (SPEC §21/§22)")
def shortlist(request: ShortlistRequest) -> ShortlistResult:
    """Simulate and rank the caller's candidate policies head-to-head."""
    return rank_shortlist(
        request.policies,
        weights=request.weights,
        objective=request.objective,
        constraints=request.constraints,
    )


def _example_entries() -> list[PolicyEntry]:
    """Three contrasting takes on the demo cordon charge (keyless example)."""
    reinvested = PolicyDSL(
        id="charge_reinvested",
        intervention=Intervention(type=InterventionType.road_pricing, amount=12.0, currency="local"),
        revenue_allocation=RevenueAllocation(public_transport=1.0, general_fund=0.0),
    )
    general_fund = PolicyDSL(
        id="charge_general_fund",
        intervention=Intervention(type=InterventionType.road_pricing, amount=12.0, currency="local"),
        revenue_allocation=RevenueAllocation(public_transport=0.0, general_fund=1.0),
    )
    pedestrianise = PolicyDSL(
        id="pedestrianise_core",
        intervention=Intervention(type=InterventionType.pedestrianisation, amount=None, currency="local"),
        revenue_allocation=RevenueAllocation(public_transport=0.5, general_fund=0.5),
    )
    return [
        PolicyEntry(label="£12 charge, reinvested in buses", policy=reinvested),
        PolicyEntry(label="£12 charge, to the general fund", policy=general_fund),
        PolicyEntry(label="Pedestrianise the core", policy=pedestrianise),
    ]


@router.get("/example", response_model=ShortlistResult, summary="Keyless: rank three contrasting demo policies")
def shortlist_example() -> ShortlistResult:
    """Rank the built-in three-way demo shortlist with balanced weights."""
    return rank_shortlist(_example_entries())
