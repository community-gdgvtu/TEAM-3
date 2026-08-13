"""Evidence / provenance trace endpoint (ROADMAP M7, SPEC §26).

``POST /evidence`` takes a compiled Policy DSL and a metric key and returns the
Evidence Drawer payload: the causal trace input-data→transform→model→
assumptions→result, the equations/parameters (behavioural levers), the named
assumptions, illustrative real-world analogues, citations and a horizon-aware
confidence. Every number is copied from the deterministic simulation; no LLM is
on the numeric path (SPEC §34).
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..evidence import ProvenanceTrace, run_evidence
from ..evidence.trace import MetricNotFound
from ..policy.dsl import PolicyDSL
from ..simulation.shocks import Shocks

router = APIRouter(prefix="/evidence", tags=["evidence"])


class EvidenceRequest(BaseModel):
    """Input to ``POST /evidence``."""

    policy: PolicyDSL = Field(description="Compiled Policy DSL (from /policy/compile).")
    metric_key: str = Field(
        description="Metric to trace, e.g. 'transit.peak_into_cbd_transit_trips'."
    )
    shocks: Shocks | None = Field(
        default=None, description="Optional exogenous stressors (applied to both worlds)."
    )
    horizon_months: float | None = Field(
        default=None,
        description="Horizon to trace at; snapped to the nearest checkpoint. "
        "Defaults to the 5-year checkpoint.",
    )


@router.post("", response_model=ProvenanceTrace, summary="Causal trace for a metric")
def evidence(req: EvidenceRequest) -> ProvenanceTrace:
    """Return the causal provenance trace for ``req.metric_key``."""
    try:
        return run_evidence(
            req.policy,
            req.metric_key,
            shocks=req.shocks,
            horizon_months=req.horizon_months,
        )
    except MetricNotFound as exc:
        raise HTTPException(
            status_code=404,
            detail={"error": str(exc), "available_metric_keys": exc.available},
        ) from exc
