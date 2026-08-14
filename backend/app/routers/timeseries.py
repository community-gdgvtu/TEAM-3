"""Time-series forecast endpoint (SPEC §7.2).

``POST /timeseries`` takes a compiled Policy DSL (plus optional shocks) and
returns, per headline metric: a seeded **synthetic monthly history** anchored to
the ABM baseline, a fitted **structural time-series forecast of World A**
(local-linear-trend + seasonal + AR(1), with prediction intervals that widen
with horizon because their variance is derived from the fit), and **World B** =
that baseline trajectory altered by the deterministic ABM policy Δ(B−A).

Synthetic history is Simulated, the statistical baseline forecast Estimated, the
policy shift Simulated. No LLM touches any number (SPEC §7.2/§8/§34).
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from ..policy.dsl import PolicyDSL
from ..simulation.shocks import Shocks
from ..timeseries.model import run_timeseries
from ..timeseries.schema import TimeSeriesForecast

router = APIRouter(prefix="/timeseries", tags=["timeseries"])


class TimeSeriesRequest(BaseModel):
    """Input to ``POST /timeseries``."""

    policy: PolicyDSL = Field(description="Compiled Policy DSL (from /policy/compile).")
    shocks: Optional[Shocks] = Field(
        default=None, description="Optional exogenous stressors applied to both worlds."
    )


@router.post(
    "", response_model=TimeSeriesForecast, summary="Time-series forecast (SPEC §7.2)"
)
def timeseries(req: TimeSeriesRequest) -> TimeSeriesForecast:
    """Forecast World A with a fitted structural model, then apply the policy Δ."""
    return run_timeseries(req.policy, shocks=req.shocks)
