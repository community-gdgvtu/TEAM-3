"""Optional exogenous shocks applied to a ``/simulate`` run (SPEC §7.7/§24).

A *shock* is a change to the shared world context that is **not** the policy —
e.g. a fuel-price spike or a background-demand surprise. Shocks are applied
identically to World A and World B so the Δ(B−A) still isolates the policy while
both worlds sit in the shocked context.

Guardrail (SPEC §34): shocks are transparent numeric overrides of named input
assumptions, applied by the deterministic model. No LLM is involved, and every
applied shock is echoed back for the Evidence Drawer.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Optional

from pydantic import BaseModel, Field

from ..baseline.params import DEFAULT_PARAMS, BaselineParams
from ..baseline.timeseries import DEFAULT_TREND, BaselineTrend


class Shocks(BaseModel):
    """Exogenous stressors layered on both worlds (all default to no-op)."""

    car_cost_per_km_multiplier: float = Field(
        1.0, gt=0, description="Fuel/running-cost shock; scales car cost per km."
    )
    transit_fare_multiplier: float = Field(
        1.0, gt=0, description="Baseline transit-fare shock; scales the flat fare."
    )
    demand_growth_per_year: Optional[float] = Field(
        default=None,
        description="Override for the exogenous background-demand growth rate.",
    )

    def is_active(self) -> bool:
        return (
            self.car_cost_per_km_multiplier != 1.0
            or self.transit_fare_multiplier != 1.0
            or self.demand_growth_per_year is not None
        )


def apply_shocks(
    shocks: Shocks | None,
    params: BaselineParams = DEFAULT_PARAMS,
    trend: BaselineTrend = DEFAULT_TREND,
) -> tuple[BaselineParams, BaselineTrend]:
    """Return (params, trend) with the shocks applied (both worlds share these)."""
    if shocks is None or not shocks.is_active():
        return params, trend
    params = replace(
        params,
        car_cost_per_km=params.car_cost_per_km * shocks.car_cost_per_km_multiplier,
        transit_fare=params.transit_fare * shocks.transit_fare_multiplier,
    )
    if shocks.demand_growth_per_year is not None:
        trend = replace(trend, demand_growth_per_year=shocks.demand_growth_per_year)
    return params, trend
