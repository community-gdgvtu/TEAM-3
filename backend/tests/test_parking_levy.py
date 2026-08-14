"""Workplace-parking-levy distinct-mechanism checks (SPEC §7.5/§34).

A workplace parking levy is *not* a flat cordon charge. It is levied on the
employer per parking space (e.g. Nottingham's WPL); employers absorb some of it
and pass the rest through, so only a fraction of the nominal levy reaches the
commuter as a behavioural signal. That makes the mode shift proportionately
smaller than an equivalent road-pricing charge every entering vehicle pays in
full. Unlike a low-emission zone it does NOT clean the fleet — it cuts emissions
purely by cutting car-km. These tests pin that a parking levy sits, distinctly,
between an LEZ and a full cordon charge, that World A and every other policy stay
byte-unchanged, and that the numbers remain Simulated + deterministic.
"""

from __future__ import annotations

from app.baseline import compute_baseline
from app.baseline.params import DEFAULT_PARAMS
from app.baseline.schema import MetricTag
from app.policy.dsl import (
    Intervention,
    InterventionType,
    PolicyDSL,
    RevenueAllocation,
)
from app.simulation import compute_world_b, derive_levers
from app.simulation.levers import DEFAULT_SIM_PARAMS


def _levy(amount: float = 12.0, pt_share: float = 0.0) -> PolicyDSL:
    return PolicyDSL(
        id="policy_levy",
        intervention=Intervention(
            type=InterventionType.parking_levy,
            amount=amount,
            currency="local",
        ),
        revenue_allocation=RevenueAllocation(
            public_transport=pt_share, general_fund=1.0 - pt_share
        ),
    )


def _charge(amount: float = 12.0, pt_share: float = 0.0) -> PolicyDSL:
    return PolicyDSL(
        id="policy_charge",
        intervention=Intervention(
            type=InterventionType.road_pricing,
            amount=amount,
            currency="local",
        ),
        revenue_allocation=RevenueAllocation(
            public_transport=pt_share, general_fund=1.0 - pt_share
        ),
    )


def _lez(amount: float = 12.0) -> PolicyDSL:
    return PolicyDSL(
        id="policy_lez",
        intervention=Intervention(
            type=InterventionType.low_emission_zone,
            amount=amount,
            currency="local",
        ),
        revenue_allocation=RevenueAllocation(public_transport=0.0, general_fund=1.0),
    )


# --- Levers: distinct mechanism -------------------------------------------


def test_levy_passes_through_only_a_fraction_of_the_charge() -> None:
    """The parking-levy per-one-way signal is the cordon charge × pass-through."""
    levy = derive_levers(_levy(amount=12.0))
    charge = derive_levers(_charge(amount=12.0))
    assert charge.charge_per_one_way > 0
    expected = charge.charge_per_one_way * DEFAULT_SIM_PARAMS.parking_levy_passthrough_share
    assert levy.charge_per_one_way == expected
    assert 0 < levy.charge_per_one_way < charge.charge_per_one_way


def test_levy_does_not_clean_the_fleet() -> None:
    """Unlike an LEZ, a parking levy leaves the CO₂-per-km factor at baseline."""
    levy = derive_levers(_levy())
    lez = derive_levers(_lez())
    assert levy.co2_factor_multiplier == 1.0
    assert lez.co2_factor_multiplier < 1.0


def test_levy_emits_its_own_behavioural_rule() -> None:
    names = {r.name for r in derive_levers(_levy()).rules}
    assert "parking_levy_charge" in names
    # It is NOT labelled as a flat cordon charge or an LEZ charge.
    assert "cordon_charge" not in names
    assert "lez_charge" not in names


# --- Model: distinct outcomes ---------------------------------------------


def test_levy_shifts_fewer_commuters_than_an_equal_cordon_charge() -> None:
    """Partial pass-through → a smaller mode shift than a full road-pricing charge."""
    base = compute_baseline()
    levy = compute_world_b(_levy(amount=12.0), reinvestment=False)
    charge = compute_world_b(_charge(amount=12.0), reinvestment=False)
    base_car = base.mode_share.car
    assert levy.mode_share.car < base_car
    assert charge.mode_share.car < base_car
    # The levy keeps strictly more cars on the road than the full charge.
    assert levy.mode_share.car > charge.mode_share.car


def test_levy_sits_between_an_lez_and_a_full_charge() -> None:
    """Three distinct pricing mechanisms: LEZ < parking levy < cordon charge."""
    lez = compute_world_b(_lez(amount=12.0), reinvestment=False)
    levy = compute_world_b(_levy(amount=12.0), reinvestment=False)
    charge = compute_world_b(_charge(amount=12.0), reinvestment=False)
    # Ordering on residual car share (more cars kept = weaker signal).
    assert lez.mode_share.car > levy.mode_share.car > charge.mode_share.car


def test_levy_still_funds_transit_reinvestment() -> None:
    """A parking levy sets a positive charge, so reinvestment engages as usual."""
    levy = derive_levers(_levy(amount=12.0, pt_share=1.0))
    assert levy.transit_fare_multiplier < 1.0
    assert levy.transit_speed_multiplier > 1.0


# --- Guardrails: World A / other policies unchanged, tags, determinism -----


def test_levy_world_b_emissions_factor_equals_baseline() -> None:
    """A parking levy must not change the emissions factor (cuts km only)."""
    levy = compute_world_b(_levy(), reinvestment=False)
    assert levy.emissions.co2_kg_per_km == DEFAULT_PARAMS.car_co2_kg_per_km


def test_road_pricing_unchanged_by_the_levy_split() -> None:
    """Removing parking_levy from the pricing family must not move road pricing."""
    charge = derive_levers(_charge(amount=12.0))
    assert charge.charge_per_one_way == 12.0 / DEFAULT_SIM_PARAMS.charge_trips_per_day
    assert {r.name for r in charge.rules} >= {"cordon_charge"}


def test_levy_metrics_are_simulated() -> None:
    levy = compute_world_b(_levy())
    for m in levy.metrics:
        assert m.tag == MetricTag.simulated


def test_levy_is_deterministic() -> None:
    a = compute_world_b(_levy(amount=15.0))
    b = compute_world_b(_levy(amount=15.0))
    assert a.mode_share.car == b.mode_share.car
    assert a.emissions.daily_co2_tonnes == b.emissions.daily_co2_tonnes
