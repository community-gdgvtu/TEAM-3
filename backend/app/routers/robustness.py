"""Decision-under-uncertainty endpoint (SPEC §20 + §21 + §22).

``POST /robustness`` takes **several candidate policies** and ranks them for a
minister facing an uncertain future: it scores each candidate under the
transparent baseline plus the SPEC §20 named shocks, builds the regret matrix,
and reports which candidate each decision criterion picks — the headline winner
(nominal), the maximin (worst-case) choice, the minimax-regret (Savage) choice,
the equal-weight (Laplace) choice, and the stress-test robustness rate.

The point it makes for the demo: the policy that wins the headline is often *not*
the one you should pick once you admit the future is uncertain.

Pure composition of the deterministic stress core — every payoff is a Simulated
Δ(B−A); no randomness, no LLM (SPEC §22/§34).
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..policy.dsl import PolicyDSL
from ..robustness.model import compare_robustness, objective_keys
from ..robustness.schema import RobustnessReport
from ..stress.catalogue import catalogue_keys

router = APIRouter(prefix="/robustness", tags=["robustness"])


class RobustnessRequest(BaseModel):
    """Input to ``POST /robustness``."""

    candidates: list[PolicyDSL] = Field(
        min_length=2,
        description="Two or more compiled Policy DSLs to compare (from /policy/compile "
        "or /optimise). Give each a distinct id.",
    )
    scenarios: list[str] | None = Field(
        default=None,
        description="Named shock keys to test against (default: all SPEC §20 shocks). "
        "See GET /stress-test/catalogue.",
    )
    objective: str | None = Field(
        default=None,
        description="Objective metric key the decision is framed around "
        "(default: emissions.daily_co2_tonnes). See GET /robustness/objectives.",
    )
    horizon_months: float | None = Field(
        default=None,
        description="Horizon; snapped to the nearest checkpoint (default 5 years). "
        "Confidence widens with the horizon.",
    )


@router.get("/objectives", summary="List the objective metrics a decision can use")
def objectives() -> dict:
    """Return the valid objective metric keys for /robustness."""
    return {
        "provenance": "Simulated",
        "note": (
            "Objectives are the flagship headline metrics; each payoff is a "
            "deterministic Δ(B−A). No LLM (SPEC §34)."
        ),
        "objectives": objective_keys(),
        "default": "emissions.daily_co2_tonnes",
    }


@router.post(
    "",
    response_model=RobustnessReport,
    summary="Rank candidate policies under uncertainty (SPEC §20/§21/§22)",
)
def robustness(req: RobustnessRequest) -> RobustnessReport:
    """Score candidates across shocks and apply the decision criteria."""
    try:
        return compare_robustness(
            req.candidates,
            scenario_keys=req.scenarios,
            objective=req.objective,
            horizon_months=req.horizon_months,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail={"error": str(exc)}) from exc
    except KeyError as exc:
        bad = exc.args[0]
        raise HTTPException(
            status_code=404,
            detail={
                "error": f"Unknown scenario or objective: {bad!r}",
                "valid_scenarios": catalogue_keys(),
                "valid_objectives": objective_keys(),
            },
        ) from exc
