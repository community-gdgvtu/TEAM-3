"""Operating-hours coverage for time-limited charges (SPEC §7.5/§34).

``intervention.active_hours`` is parsed from the policy text and surfaced as
provenance, but until now it never touched the numbers: a peak-only congestion
charge produced byte-identical traffic/emissions/revenue to an all-day one. That
is dishonest — a scheme that only operates for part of the inbound commute peak
prices fewer commuters and raises less revenue. These tests pin the honest
behaviour: the charge's per-trip signal scales by how much of the AM inbound peak
its operating window covers, the all-day default stays unchanged, and the three
pricing mechanisms all respect it.
"""

from __future__ import annotations

from app.policy.dsl import (
    ActiveHours,
    Intervention,
    InterventionType,
    PolicyDSL,
    RevenueAllocation,
)
from app.simulation.levers import (
    DEFAULT_SIM_PARAMS,
    _active_hours_coverage,
    derive_levers,
)


def _policy(itype: InterventionType, amount: float, start: str, end: str) -> PolicyDSL:
    return PolicyDSL(
        intervention=Intervention(
            type=itype,
            amount=amount,
            currency="GBP",
            active_hours=ActiveHours(start=start, end=end),
        ),
        revenue_allocation=RevenueAllocation(public_transport=0.0),
    )


# --- coverage function --------------------------------------------------------

def test_coverage_full_when_window_contains_peak() -> None:
    # Default all-day window 07:00–19:00 fully contains the 07:00–10:00 peak.
    cov = _active_hours_coverage(ActiveHours(start="07:00", end="19:00"), DEFAULT_SIM_PARAMS)
    assert cov == 1.0


def test_coverage_partial_when_window_clips_peak() -> None:
    # 07:00–09:00 covers 2h of the 3h (07:00–10:00) peak.
    cov = _active_hours_coverage(ActiveHours(start="07:00", end="09:00"), DEFAULT_SIM_PARAMS)
    assert abs(cov - (2.0 / 3.0)) < 1e-9


def test_coverage_zero_when_window_misses_peak() -> None:
    # An afternoon/evening-only charge does nothing to the morning inbound peak.
    cov = _active_hours_coverage(ActiveHours(start="16:00", end="19:00"), DEFAULT_SIM_PARAMS)
    assert cov == 0.0


def test_coverage_degenerate_window_falls_back_to_one() -> None:
    # An uninterpretable/degenerate window must NOT silently zero the charge.
    assert _active_hours_coverage(ActiveHours(start="19:00", end="07:00"), DEFAULT_SIM_PARAMS) == 1.0
    assert _active_hours_coverage(ActiveHours(start="bad", end="value"), DEFAULT_SIM_PARAMS) == 1.0


# --- effect on the derived charge --------------------------------------------

def test_all_day_charge_is_unchanged_regression() -> None:
    # The default all-day window keeps the cordon charge byte-identical to
    # amount / trips_per_day (coverage 1.0), so existing numbers never move.
    p = _policy(InterventionType.road_pricing, 10.0, "07:00", "19:00")
    lev = derive_levers(p)
    expected = 10.0 / DEFAULT_SIM_PARAMS.charge_trips_per_day
    assert abs(lev.charge_per_one_way - expected) < 1e-12
    # No active-hours rule is emitted when it does not bite.
    assert not any(r.name == "active_hours_coverage" for r in lev.rules)


def test_peak_only_charge_is_weaker_than_all_day() -> None:
    all_day = derive_levers(_policy(InterventionType.road_pricing, 10.0, "07:00", "19:00"))
    peak_only = derive_levers(_policy(InterventionType.road_pricing, 10.0, "07:00", "09:00"))
    assert peak_only.charge_per_one_way < all_day.charge_per_one_way
    # 2/3 coverage → 2/3 of the signal.
    assert abs(peak_only.charge_per_one_way - all_day.charge_per_one_way * (2.0 / 3.0)) < 1e-9
    # And it is surfaced as its own behavioural rule for the Evidence Drawer.
    cov_rule = next(r for r in peak_only.rules if r.name == "active_hours_coverage")
    # The surfaced rule value is rounded to 4 dp for display.
    assert abs(cov_rule.value - (2.0 / 3.0)) < 1e-3


def test_off_peak_charge_barely_bites() -> None:
    off_peak = derive_levers(_policy(InterventionType.road_pricing, 10.0, "16:00", "19:00"))
    assert off_peak.charge_per_one_way == 0.0


def test_coverage_applies_to_lez_and_parking_levy_too() -> None:
    # Both distinct pricing mechanisms scale by the same operating-hours coverage.
    for itype in (InterventionType.low_emission_zone, InterventionType.parking_levy):
        all_day = derive_levers(_policy(itype, 12.0, "07:00", "19:00"))
        peak_only = derive_levers(_policy(itype, 12.0, "07:00", "09:00"))
        assert all_day.charge_per_one_way > 0.0
        assert abs(
            peak_only.charge_per_one_way - all_day.charge_per_one_way * (2.0 / 3.0)
        ) < 1e-9


def test_pricing_ordering_preserved_under_partial_coverage() -> None:
    # The LEZ < parking-levy < cordon ordering on residual signal still holds when
    # all three run on the same narrowed window (coverage is a common factor).
    lez = derive_levers(_policy(InterventionType.low_emission_zone, 12.0, "07:00", "09:00"))
    levy = derive_levers(_policy(InterventionType.parking_levy, 12.0, "07:00", "09:00"))
    cordon = derive_levers(_policy(InterventionType.road_pricing, 12.0, "07:00", "09:00"))
    assert lez.charge_per_one_way < levy.charge_per_one_way < cordon.charge_per_one_way
