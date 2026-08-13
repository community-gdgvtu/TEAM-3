"""Counterfactual comparison: World A vs B vs amended C/D… (ROADMAP M7, SPEC §21).

SPEC §21 requires that intervention metrics are never shown without the
baseline, and that additional worlds (an opposition amendment, an optimised
policy) can be compared side by side against it. This module assembles one
payload holding:

* **World A** — the no-intervention baseline (snapshot + trajectory),
* **World B** — the compiled policy (intervention),
* **World C, D…** — one per supplied amendment,

each carrying its Δ-vs-baseline and Δ-vs-intervention, plus a compact headline
table (baseline + every world + Δ per metric at one horizon) the dashboard can
render directly.

Guardrail (SPEC §34): amendments only edit the *structured policy*; every number
comes from the same deterministic model, so all worlds/deltas are Simulated. No
LLM is on the numeric path.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from ..baseline.model import compute_baseline
from ..baseline.schema import BaselineMetrics, BaselineTimeSeries, Checkpoint, MetricTag
from ..baseline.timeseries import build_timeseries
from ..policy.dsl import PolicyDSL
from .amendment import Amendment, apply_amendment
from .compare import build_delta
from .model import compute_world_b
from .schema import DeltaTimeSeries, WorldBMetrics, WorldBTimeSeries
from .shocks import Shocks, apply_shocks
from .timeline import build_world_b_timeline

# World ids beyond the baseline (A) and the intervention (B).
_WORLD_IDS = ["B", "C", "D", "E", "F", "G", "H"]


class WorldAResult(BaseModel):
    snapshot: BaselineMetrics
    timeseries: BaselineTimeSeries


class CounterfactualWorld(BaseModel):
    """One intervention world (B, C, D…) with its deltas."""

    id: str = Field(description="World id, e.g. 'B' (intervention) or 'C' (amendment).")
    role: str = Field(description="'intervention' | 'amendment'.")
    label: str = Field(description="Human name for the world.")
    policy_id: str
    changes: list[str] = Field(
        default_factory=list, description="Concrete edits vs the base policy (amendments)."
    )
    snapshot: WorldBMetrics
    timeseries: WorldBTimeSeries
    delta_vs_baseline: DeltaTimeSeries = Field(description="Δ(world − World A).")
    delta_vs_intervention: DeltaTimeSeries | None = Field(
        default=None, description="Δ(world − World B); None for World B itself."
    )


class ComparisonCell(BaseModel):
    """One world's value for one metric at the headline horizon."""

    world_id: str
    value: float
    delta_vs_baseline: float
    delta_pct: float | None = None


class ComparisonRow(BaseModel):
    """One metric across all worlds at the headline horizon."""

    key: str
    label: str
    unit: str
    tag: MetricTag = MetricTag.simulated
    baseline_value: float = Field(description="World-A value (never omitted, SPEC §21).")
    cells: list[ComparisonCell] = Field(default_factory=list)


class CounterfactualComparison(BaseModel):
    """World A vs B vs amended C/D… in one payload (SPEC §21)."""

    provenance: MetricTag = Field(MetricTag.simulated)
    note: str = Field(
        default=(
            "Counterfactual set: World A (baseline) vs World B (intervention) vs any "
            "amendment worlds, all from the same deterministic model. Δ outcome = "
            "world − World A; the baseline is always present (SPEC §21/§34)."
        )
    )
    base_policy_id: str
    horizon: Checkpoint = Field(description="Horizon the headline table is quoted at.")
    world_a: WorldAResult
    worlds: list[CounterfactualWorld] = Field(default_factory=list)
    headline_table: list[ComparisonRow] = Field(
        default_factory=list, description="Baseline + every world + Δ per metric (SPEC §21)."
    )


def _pick_point(series, horizon_months: float | None):
    if horizon_months is None:
        for p in series.points:
            if p.t_months == 60.0:
                return p
        return series.points[-1]
    return min(series.points, key=lambda p: abs(p.t_months - horizon_months))


def compare_counterfactuals(
    policy: PolicyDSL,
    amendments: list[Amendment] | None = None,
    *,
    shocks: Shocks | None = None,
    horizon_months: float | None = None,
) -> CounterfactualComparison:
    """Build the A / B / C… counterfactual payload for ``policy``."""
    amendments = amendments or []
    params, trend = apply_shocks(shocks)

    base = compute_baseline(params)
    base_ts = build_timeseries(base, trend)

    # World B — the intervention itself.
    intervention_specs = [("B", "intervention", "Intervention", policy, [])]
    for i, amd in enumerate(amendments):
        wid = _WORLD_IDS[min(i + 1, len(_WORLD_IDS) - 1)]
        amended = apply_amendment(policy, amd)
        intervention_specs.append((wid, "amendment", amd.label, amended, amd.describe()))

    worlds: list[CounterfactualWorld] = []
    b_ts_ref: WorldBTimeSeries | None = None
    for wid, role, label, wpolicy, changes in intervention_specs:
        snapshot = compute_world_b(wpolicy, params=params, reinvestment=True)
        w_ts = build_world_b_timeline(wpolicy, baseline=base, params=params, trend=trend)
        delta_vs_baseline = build_delta(base_ts, w_ts)
        if wid == "B":
            b_ts_ref = w_ts
            delta_vs_intervention = None
        else:
            delta_vs_intervention = build_delta(b_ts_ref, w_ts) if b_ts_ref else None
        worlds.append(
            CounterfactualWorld(
                id=wid,
                role=role,
                label=label,
                policy_id=wpolicy.id,
                changes=changes,
                snapshot=snapshot,
                timeseries=w_ts,
                delta_vs_baseline=delta_vs_baseline,
                delta_vs_intervention=delta_vs_intervention,
            )
        )

    # Headline table: one row per metric, baseline + each world at the horizon.
    checkpoint: Checkpoint | None = None
    rows: list[ComparisonRow] = []
    ref_delta = worlds[0].delta_vs_baseline  # World B provides the metric list.
    for series in ref_delta.series:
        cells: list[ComparisonCell] = []
        baseline_value: float | None = None
        for w in worlds:
            w_series = next((s for s in w.delta_vs_baseline.series if s.key == series.key), None)
            if w_series is None:
                continue
            pt = _pick_point(w_series, horizon_months)
            if checkpoint is None:
                checkpoint = Checkpoint(
                    label=f"{pt.t_months:g}m",
                    t_months=pt.t_months,
                    t_years=round(pt.t_months / 12.0, 3),
                )
            baseline_value = pt.world_a
            cells.append(
                ComparisonCell(
                    world_id=w.id,
                    value=round(pt.world_b, 3),
                    delta_vs_baseline=round(pt.delta, 3),
                    delta_pct=pt.delta_pct,
                )
            )
        rows.append(
            ComparisonRow(
                key=series.key,
                label=series.label,
                unit=series.unit,
                tag=series.tag,
                baseline_value=round(baseline_value or 0.0, 3),
                cells=cells,
            )
        )

    if checkpoint is None:  # pragma: no cover - defensive (no metrics)
        checkpoint = Checkpoint(label="60m", t_months=60.0, t_years=5.0)

    return CounterfactualComparison(
        base_policy_id=policy.id,
        horizon=checkpoint,
        world_a=WorldAResult(snapshot=base, timeseries=base_ts),
        worlds=worlds,
        headline_table=rows,
    )
