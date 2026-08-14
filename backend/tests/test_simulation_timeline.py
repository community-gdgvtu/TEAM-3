"""World-B staged-adaptation timeline checks — ROADMAP M3, SPEC §9/§24/§34.

Assertions are structural/directional so they survive re-tuning of the
:class:`~app.simulation.timeline.AdaptationParams`, plus the guardrails that the
band widens with the horizon and every point is tagged Simulated.
"""

from __future__ import annotations

from app.baseline import compute_baseline
from app.baseline.schema import MetricTag
from app.policy.dsl import (
    Intervention,
    InterventionType,
    PolicyDSL,
    RevenueAllocation,
)
from app.simulation import build_world_b_timeline, compute_world_b


def _pricing_policy(amount: float = 12.0, pt_share: float = 1.0) -> PolicyDSL:
    return PolicyDSL(
        id="policy_test_timeline",
        intervention=Intervention(
            type=InterventionType.road_pricing,
            amount=amount,
            currency="local",
            geographic_zone="cbd_polygon",
        ),
        revenue_allocation=RevenueAllocation(
            public_transport=pt_share, general_fund=1.0 - pt_share
        ),
    )


def _car_series(ts):
    return next(s for s in ts.series if s.key == "mode_share.car_pct")


def test_timeline_has_all_default_checkpoints() -> None:
    ts = build_world_b_timeline(_pricing_policy())
    labels = [c.label for c in ts.checkpoints]
    assert labels == ["T0", "1 month", "3 months", "5 months", "1 year", "2 years", "5 years", "10 years"]
    for s in ts.series:
        assert len(s.points) == len(ts.checkpoints)


def test_t0_starts_at_baseline_not_full_policy() -> None:
    # At T0 no behaviour has adapted yet, so World B == World A for that metric.
    base = compute_baseline()
    ts = build_world_b_timeline(_pricing_policy())
    car = _car_series(ts)
    base_car = next(m.value for m in base.metrics if m.key == "mode_share.car_pct")
    assert car.points[0].t_months == 0.0
    assert abs(car.points[0].value - base_car) < 1e-6


def test_car_share_declines_and_converges_to_full_policy() -> None:
    # A cordon charge pulls commuters off cars; the trajectory should fall
    # monotonically from baseline toward the fully-adapted World-B level.
    base = compute_baseline()
    wb = compute_world_b(_pricing_policy(), reinvestment=True)
    ts = build_world_b_timeline(_pricing_policy())
    car = _car_series(ts)
    base_car = next(m.value for m in base.metrics if m.key == "mode_share.car_pct")
    full_car = next(m.value for m in wb.metrics if m.key == "mode_share.car_pct")

    values = [p.value for p in car.points]
    assert values[0] == base_car
    # Non-increasing (charge only reduces car share as adaptation lands).
    assert all(b <= a + 1e-6 for a, b in zip(values, values[1:]))
    # 10-year end-state is essentially the fully-adapted policy level.
    assert abs(values[-1] - full_car) / max(1.0, abs(full_car)) < 0.05


def test_confidence_band_widens_monotonically() -> None:
    ts = build_world_b_timeline(_pricing_policy())
    for s in ts.series:
        widths = [p.high - p.low for p in s.points]
        assert all(b >= a - 1e-9 for a, b in zip(widths, widths[1:]))
    # And the band must actually be non-trivial at the long horizon.
    car = _car_series(ts)
    assert (car.points[-1].high - car.points[-1].low) > 0


def test_transit_ramp_lags_behaviour_substitution() -> None:
    # Transit boardings keep rising after the short-run months as the
    # revenue-funded capacity ramp phases in mid-run.
    ts = build_world_b_timeline(_pricing_policy(pt_share=1.0))
    boardings = next(s for s in ts.series if s.key == "transit.daily_transit_trips")
    vals = [p.value for p in boardings.points]
    # 5-month value < 5-year value: mid/long-run reinvestment adds more transit.
    idx_5m = [c.label for c in ts.checkpoints].index("5 months")
    idx_5y = [c.label for c in ts.checkpoints].index("5 years")
    assert vals[idx_5y] > vals[idx_5m]


def test_timeline_points_tagged_simulated() -> None:
    ts = build_world_b_timeline(_pricing_policy())
    assert ts.provenance == MetricTag.simulated
    for s in ts.series:
        assert s.tag == MetricTag.simulated
        assert s.tag != MetricTag.generated


def test_timeline_is_deterministic() -> None:
    p = _pricing_policy()
    a = build_world_b_timeline(p)
    b = build_world_b_timeline(p)
    assert [pt.value for s in a.series for pt in s.points] == [
        pt.value for s in b.series for pt in s.points
    ]
