"""Compute Δ(World B − World A) trajectories from two aligned time series.

The baseline (:class:`~app.baseline.schema.BaselineTimeSeries`) and the World-B
projection (:class:`~app.simulation.schema.WorldBTimeSeries`) are built over the
*same* checkpoint grid and the *same* metric keys, so the policy effect at each
horizon is simply the pointwise difference. This module assembles that into a
:class:`~app.simulation.schema.DeltaTimeSeries` for ``POST /simulate`` (SPEC §5/§21).

Guardrail (SPEC §34): the delta is an arithmetic transform of two Simulated
series — no LLM, tagged Simulated.
"""

from __future__ import annotations

import math

from ..baseline.schema import BaselineTimeSeries
from .schema import (
    DeltaPoint,
    DeltaSeries,
    DeltaTimeSeries,
    WorldBTimeSeries,
)


def build_delta(
    world_a: BaselineTimeSeries | WorldBTimeSeries,
    world_b: WorldBTimeSeries,
) -> DeltaTimeSeries:
    """Build a Δ time series from two aligned projections.

    The canonical use is Δ(World B − World A). Because both time-series types
    expose the same ``.series`` (:class:`~app.baseline.schema.MetricSeries`) and
    ``.checkpoints``, the same routine also compares two World-B runs — used by
    the amendment loop to compute Δ(amended − original) (SPEC §12).
    """
    a_by_key = {s.key: s for s in world_a.series}

    series: list[DeltaSeries] = []
    for b in world_b.series:
        a = a_by_key.get(b.key)
        if a is None or len(a.points) != len(b.points):
            # Only compare metrics that exist in both worlds on the same grid.
            continue
        points: list[DeltaPoint] = []
        for ap, bp in zip(a.points, b.points):
            delta = bp.value - ap.value
            # Combine the two independent-ish bands in quadrature (RSS).
            a_half = (ap.high - ap.low) / 2.0
            b_half = (bp.high - bp.low) / 2.0
            half = math.sqrt(a_half * a_half + b_half * b_half)
            delta_pct = (
                round(100.0 * delta / ap.value, 2) if abs(ap.value) > 1e-9 else None
            )
            points.append(
                DeltaPoint(
                    t_months=bp.t_months,
                    world_a=ap.value,
                    world_b=bp.value,
                    delta=round(delta, 3),
                    delta_pct=delta_pct,
                    low=round(delta - half, 3),
                    high=round(delta + half, 3),
                )
            )
        series.append(
            DeltaSeries(key=b.key, label=b.label, unit=b.unit, points=points)
        )

    return DeltaTimeSeries(checkpoints=list(world_b.checkpoints), series=series)
