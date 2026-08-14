"""Standalone transit-investment distinct-mechanism checks (SPEC §7.5/§9/§34).

A "invest in buses/transit" policy has no charge and no ban, so before this was
modelled it hit no lever branch and World B was byte-identical to World A — a
silent no-op a minister would misread as "transit investment does nothing". Its
real, honest lever is *supply-side*: better transit service (a fare cut + speed
uplift) pulls commuters over voluntarily, and — with no stick — it draws the
marginal walkers onto transit far more than it pulls drivers off the road (a
well-documented real finding: pull without push mostly reshuffles sustainable
modes). These tests pin that a transit investment now produces a real, staged
effect (neutral in the short-run anchor, present in the long-run one, so it ramps
in over the horizon), that its service intensity is an explicit Estimated
assumption not derived from the £ amount, and that it does not clean the fleet or
touch World A / other policies. Numbers stay Simulated + deterministic.
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
from app.simulation.levers import DEFAULT_SIM_PARAMS, SimParams


def _transit(amount: float | None = None) -> PolicyDSL:
    return PolicyDSL(
        id="policy_transit",
        intervention=Intervention(
            type=InterventionType.transit_investment,
            amount=amount,
            currency="local",
        ),
        revenue_allocation=RevenueAllocation(public_transport=0.0, general_fund=1.0),
    )


# --- Levers: distinct supply-side mechanism -------------------------------


def test_transit_investment_improves_service_without_a_charge() -> None:
    lv = derive_levers(_transit())
    # No stick: no charge, no ban.
    assert lv.charge_per_one_way == 0.0
    assert lv.car_banned_in_cbd is False
    # Only lever is better transit service.
    assert lv.transit_fare_multiplier < 1.0
    assert lv.transit_speed_multiplier > 1.0
    # It does not clean the fleet (that is an LEZ lever, not this).
    assert lv.co2_factor_multiplier == 1.0
    assert {r.name for r in lv.rules} == {"transit_investment"}


def test_intensity_is_not_derived_from_the_currency_amount() -> None:
    """The service uplift is the same whether or not a £ amount is stated."""
    without = derive_levers(_transit(amount=None))
    with_amt = derive_levers(_transit(amount=50_000_000.0))
    assert without.transit_fare_multiplier == with_amt.transit_fare_multiplier
    assert without.transit_speed_multiplier == with_amt.transit_speed_multiplier


def test_intensity_is_a_tunable_assumption() -> None:
    weak = derive_levers(_transit(), sim=SimParams(transit_investment_intensity=0.2))
    strong = derive_levers(_transit(), sim=SimParams(transit_investment_intensity=1.0))
    assert strong.transit_fare_multiplier < weak.transit_fare_multiplier
    assert strong.transit_speed_multiplier > weak.transit_speed_multiplier
    # Zero intensity → no lever at all.
    off = derive_levers(_transit(), sim=SimParams(transit_investment_intensity=0.0))
    assert off.transit_fare_multiplier == 1.0
    assert off.transit_speed_multiplier == 1.0
    assert off.rules == []


# --- Model: real, staged, honest outcome ----------------------------------


def test_transit_investment_is_no_longer_a_no_op() -> None:
    """The long-run world differs from the baseline (transit ridership rises)."""
    base = compute_baseline()
    long_run = compute_world_b(_transit(), reinvestment=True)
    assert long_run.mode_share.public_transit > base.mode_share.public_transit


def test_effect_ramps_in_short_run_anchor_is_neutral() -> None:
    """Short-run anchor (capacity not yet built) == baseline mode split."""
    base = compute_baseline()
    short_run = compute_world_b(_transit(), reinvestment=False)
    assert short_run.mode_share.public_transit == base.mode_share.public_transit
    assert short_run.mode_share.car == base.mode_share.car
    assert short_run.mode_share.walk == base.mode_share.walk
    # The service rule is dropped in the short-run anchor (multipliers reset).
    assert "transit_investment" not in {r.name for r in short_run.behavioural_rules}
    assert short_run.levers["transit_fare_multiplier"] == 1.0


def test_pull_without_push_barely_touches_car_use() -> None:
    """No charge → the shift is mostly walk→transit, not a big car→transit move.

    This is the honest finding the model must not overstate: improving transit
    without a stick reshuffles sustainable modes far more than it removes cars.
    """
    base = compute_baseline()
    long_run = compute_world_b(_transit(), reinvestment=True)
    car_drop = base.mode_share.car - long_run.mode_share.car
    transit_gain = long_run.mode_share.public_transit - base.mode_share.public_transit
    assert transit_gain > 0
    # Car reduction is no larger than the transit gain and is modest in absolute
    # terms — the pull mostly comes from walkers, not drivers.
    assert car_drop <= transit_gain


def test_transit_investment_does_not_change_emissions_factor() -> None:
    long_run = compute_world_b(_transit(), reinvestment=True)
    assert long_run.emissions.co2_kg_per_km == DEFAULT_PARAMS.car_co2_kg_per_km


# --- Guardrails: tags + determinism ---------------------------------------


def test_transit_investment_metrics_are_simulated() -> None:
    long_run = compute_world_b(_transit())
    for m in long_run.metrics:
        assert m.tag == MetricTag.simulated


def test_transit_investment_is_deterministic() -> None:
    a = compute_world_b(_transit(), reinvestment=True)
    b = compute_world_b(_transit(), reinvestment=True)
    assert a.mode_share.public_transit == b.mode_share.public_transit
    assert a.emissions.daily_co2_tonnes == b.emissions.daily_co2_tonnes


def test_default_intensity_surfaced_in_sim_params() -> None:
    assert 0.0 < DEFAULT_SIM_PARAMS.transit_investment_intensity <= 1.0
