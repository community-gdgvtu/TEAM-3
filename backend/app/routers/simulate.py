"""Policy simulation endpoint (ROADMAP M3, SPEC §5/§7.7/§21).

``POST /simulate`` takes a compiled Policy DSL (plus optional exogenous shocks
and a seed) and returns, across the Time Machine checkpoints:

* **World A** — the no-intervention baseline (snapshot + trajectory),
* **World B** — the policy state with staged adaptation (snapshot + trajectory),
* **Δ(B − A)** — the isolated policy effect per metric at every checkpoint.

Every number is produced by the deterministic agent-based model and tagged
Simulated; no LLM touches the numeric path (SPEC §34). The model is deterministic,
so ``seed`` does not change any number — it is accepted and echoed for API
symmetry / future stochastic extensions.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from ..baseline.model import compute_baseline
from ..baseline.schema import BaselineMetrics, BaselineTimeSeries, MetricTag
from ..baseline.timeseries import build_timeseries
from ..policy.dsl import PolicyDSL
from ..simulation.compare import build_delta
from ..simulation.model import compute_world_b
from ..simulation.schema import DeltaTimeSeries, WorldBMetrics, WorldBTimeSeries
from ..simulation.shocks import Shocks, apply_shocks
from ..simulation.timeline import build_world_b_timeline

router = APIRouter(prefix="/simulate", tags=["simulate"])


class SimulateRequest(BaseModel):
    """Input to ``POST /simulate``."""

    policy: PolicyDSL = Field(description="Compiled Policy DSL (from /policy/compile).")
    shocks: Optional[Shocks] = Field(
        default=None, description="Optional exogenous stressors applied to both worlds."
    )
    seed: Optional[int] = Field(
        default=None,
        description="Accepted for API symmetry; the model is deterministic so it "
        "does not alter any number.",
    )


class WorldAResult(BaseModel):
    snapshot: BaselineMetrics
    timeseries: BaselineTimeSeries


class WorldBResult(BaseModel):
    snapshot: WorldBMetrics
    timeseries: WorldBTimeSeries


class SimulateResponse(BaseModel):
    """World A, World B and Δ(B−A) across the Time Machine checkpoints."""

    provenance: MetricTag = Field(MetricTag.simulated)
    policy_id: str
    note: str = Field(
        default=(
            "Deterministic agent-based simulation. World A = baseline, World B = "
            "policy with staged adaptation, Δ = B − A per metric per checkpoint. "
            "No LLM produced any number (SPEC §34)."
        )
    )
    world_a: WorldAResult
    world_b: WorldBResult
    delta: DeltaTimeSeries
    shocks_applied: dict = Field(
        default_factory=dict, description="Echo of the shocks used (auditable)."
    )
    seed: Optional[int] = None


@router.post("", response_model=SimulateResponse, summary="Simulate a policy → A / B / Δ")
def simulate(req: SimulateRequest) -> SimulateResponse:
    """Run World A, World B and their delta for the supplied policy.

    Shocks (when present) are applied to both worlds so the delta still isolates
    the intervention. All outputs are Simulated (SPEC §34).
    """
    params, trend = apply_shocks(req.shocks)

    # World A (baseline) under the shocked context.
    base = compute_baseline(params)
    base_ts = build_timeseries(base, trend)

    # World B: full and reinvestment-off anchors drive the staged-adaptation ramp.
    b_full = compute_world_b(req.policy, params=params, reinvestment=True)
    b_behav = compute_world_b(req.policy, params=params, reinvestment=False)
    b_ts = build_world_b_timeline(
        req.policy,
        baseline=base,
        world_b_full=b_full,
        world_b_behaviour=b_behav,
        params=params,
        trend=trend,
    )

    delta = build_delta(base_ts, b_ts)

    return SimulateResponse(
        policy_id=req.policy.id,
        world_a=WorldAResult(snapshot=base, timeseries=base_ts),
        world_b=WorldBResult(snapshot=b_full, timeseries=b_ts),
        delta=delta,
        shocks_applied=(req.shocks.model_dump() if req.shocks else {}),
        seed=req.seed,
    )
