"""Baseline (World A) endpoint (ROADMAP M2, SPEC §5/§9).

``GET /baseline`` returns the no-intervention reference: the structural snapshot
(mode share / traffic / emissions proxy / transit demand) plus each headline
metric projected as a **time series** across the Time Machine checkpoints, with a
horizon-widening confidence band (SPEC §9). No LLM produces any number here
(SPEC §34); the values come from the deterministic agent-based model.
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from ..baseline import BaselineMetrics, BaselineTimeSeries, cached_baseline, cached_timeseries
from ..baseline.schema import MetricTag

router = APIRouter(prefix="/baseline", tags=["baseline"])


class BaselineResponse(BaseModel):
    """Combined World-A snapshot + timeline projection."""

    world: str = Field("A", description="'A' = baseline, no intervention (SPEC §5).")
    provenance: MetricTag = Field(MetricTag.simulated)
    snapshot: BaselineMetrics = Field(description="Present-day World-A state (T0).")
    timeseries: BaselineTimeSeries = Field(
        description="World-A metric trajectories across the Time Machine checkpoints."
    )


@router.get("", response_model=BaselineResponse, summary="Baseline metrics + time series")
def get_baseline() -> BaselineResponse:
    """Return the baseline snapshot and its metric time series.

    Both are cached deterministic outputs of the structural model, so repeated
    calls are identical for a given dataset. Every number is tagged Simulated for
    the Evidence Drawer (SPEC §26).
    """
    return BaselineResponse(
        snapshot=cached_baseline(),
        timeseries=cached_timeseries(),
    )
