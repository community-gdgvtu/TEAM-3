"""Re-run the deterministic A/B/Δ core with user-overridden assumptions.

SPEC §34.10 ("users can change assumptions and rerun"). This reuses the exact
pipeline `/simulate` runs — ``compute_baseline`` / ``compute_world_b`` /
``build_world_b_timeline`` / ``build_delta`` — with one or more documented
assumptions replaced, and contrasts the result against the default-assumption
run so the user sees precisely how much their change moved the headline. No new
numeric model, no LLM (SPEC §34).
"""

from __future__ import annotations

from dataclasses import replace

from ..baseline.model import compute_baseline
from ..baseline.params import BaselineParams
from ..baseline.schema import Checkpoint
from ..baseline.timeseries import build_timeseries
from ..policy.dsl import PolicyDSL
from ..simulation.compare import build_delta
from ..simulation.levers import SimParams
from ..simulation.model import compute_world_b
from ..simulation.schema import DeltaTimeSeries
from ..simulation.shocks import Shocks, apply_shocks
from ..simulation.timeline import build_world_b_timeline
from .catalogue import assumption_index
from .schema import (
    AppliedOverride,
    AssumptionRerunResponse,
    MetricContrast,
)

# Re-export the response type under a friendlier name for the package __init__.
AssumptionRerunResult = AssumptionRerunResponse


class UnknownAssumption(LookupError):
    """Raised when an override names an assumption not in the catalogue."""

    def __init__(self, name: str, available: list[str]) -> None:
        self.name = name
        self.available = available
        super().__init__(
            f"Unknown assumption {name!r}. Overridable: {', '.join(available)}"
        )


def _apply_overrides(
    base_params: BaselineParams,
    sim_params: SimParams,
    applied: dict[str, float],
    index,
) -> tuple[BaselineParams, SimParams]:
    """Return (BaselineParams, SimParams) with the applied overrides set."""
    base_kw = {
        index[n].field: v for n, v in applied.items() if index[n].target == "base"
    }
    sim_kw = {
        index[n].field: v for n, v in applied.items() if index[n].target == "sim"
    }
    bp = replace(base_params, **base_kw) if base_kw else base_params
    sp = replace(sim_params, **sim_kw) if sim_kw else sim_params
    return bp, sp


def _run(
    policy: PolicyDSL,
    base_params: BaselineParams,
    sim_params: SimParams,
    trend: dict,
):
    """Full deterministic A/B/Δ run — mirrors /simulate exactly."""
    base = compute_baseline(base_params)
    base_ts = build_timeseries(base, trend)
    b_full = compute_world_b(policy, params=base_params, sim=sim_params, reinvestment=True)
    b_behav = compute_world_b(policy, params=base_params, sim=sim_params, reinvestment=False)
    b_ts = build_world_b_timeline(
        policy,
        baseline=base,
        world_b_full=b_full,
        world_b_behaviour=b_behav,
        params=base_params,
        trend=trend,
    )
    delta = build_delta(base_ts, b_ts)
    return base, b_full, delta


def _horizon_index(delta: DeltaTimeSeries, horizon_months: float | None) -> int:
    checkpoints = [c.t_months for c in delta.checkpoints]
    if not checkpoints:
        return 0
    if horizon_months is None:
        return checkpoints.index(24.0) if 24.0 in checkpoints else len(checkpoints) - 1
    return min(range(len(checkpoints)), key=lambda i: abs(checkpoints[i] - horizon_months))


def rerun_with_assumptions(
    policy: PolicyDSL,
    overrides: dict[str, float],
    *,
    shocks: Shocks | None = None,
    horizon_months: float | None = None,
) -> AssumptionRerunResponse:
    """Re-run A/B/Δ with ``overrides`` applied and contrast vs the defaults.

    ``overrides`` maps assumption name → requested value. Unknown names raise
    :class:`UnknownAssumption`; out-of-range values are clamped to the documented
    plausible range and flagged (honest per SPEC §34) rather than silently used.
    """
    index = assumption_index()
    for name in overrides:
        if name not in index:
            raise UnknownAssumption(name, sorted(index))

    base_params, trend = apply_shocks(shocks)
    sim_params = SimParams()

    # --- Default-assumption run (the baseline to contrast against). ---
    _, _, default_delta = _run(policy, base_params, sim_params, trend)
    h_idx = _horizon_index(default_delta, horizon_months)
    horizon = default_delta.checkpoints[h_idx]

    # --- Validate + clamp each override to its documented plausible range. ---
    applied_map: dict[str, float] = {}
    applied_cards: list[AppliedOverride] = []
    for name, requested in overrides.items():
        spec = index[name]
        req = float(requested)
        lo, hi = float(spec.low), float(spec.high)
        applied = min(hi, max(lo, req))
        in_range = lo - 1e-12 <= req <= hi + 1e-12
        clamped = abs(applied - req) > 1e-12
        note = (
            f"Requested {req:g} is outside the plausible range [{lo:g}, {hi:g}]; "
            f"clamped to {applied:g}."
            if clamped
            else ""
        )
        applied_map[name] = applied
        applied_cards.append(
            AppliedOverride(
                name=name,
                label=spec.label,
                unit=spec.unit,
                default=float(spec.default),
                low=lo,
                high=hi,
                requested=req,
                applied=applied,
                in_range=in_range,
                clamped=clamped,
                note=note,
            )
        )

    # --- Overridden-assumption run. ---
    bp, sp = _apply_overrides(base_params, sim_params, applied_map, index)
    base_o, b_full_o, over_delta = _run(policy, bp, sp, trend)

    # --- Per-metric contrast at the horizon. ---
    default_at = {s.key: s.points[h_idx].delta for s in default_delta.series}
    contrast: list[MetricContrast] = []
    for s in over_delta.series:
        d_over = s.points[h_idx].delta
        d_def = default_at.get(s.key, d_over)
        shift = d_over - d_def
        shift_pct = round(shift / abs(d_def) * 100.0, 2) if abs(d_def) > 1e-9 else None
        contrast.append(
            MetricContrast(
                key=s.key,
                label=s.label,
                unit=s.unit,
                default_delta=round(d_def, 4),
                overridden_delta=round(d_over, 4),
                shift=round(shift, 4),
                shift_pct_of_default=shift_pct,
            )
        )

    return AssumptionRerunResponse(
        policy_id=policy.id,
        horizon=Checkpoint(
            label=horizon.label, t_months=horizon.t_months, t_years=horizon.t_years
        ),
        overrides=applied_cards,
        contrast=contrast,
        world_a_snapshot=base_o,
        world_b_snapshot=b_full_o,
        delta=over_delta,
        shocks_applied=(shocks.model_dump() if shocks else {}),
    )
