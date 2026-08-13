"""Low-emission-zone distinct-mechanism checks (SPEC §7.5/§34).

A low-emission zone is *not* a flat congestion charge: only the non-compliant
share of the fleet pays, and the zone's dominant lever is fleet turnover toward
cleaner vehicles (a lower CO₂-per-km factor in World B only). These tests pin
that an LEZ behaves distinctly from an equivalent road-pricing charge, that the
fleet-cleanup lever is World-B only (World A and every non-LEZ policy are
unchanged), and that the numbers stay Simulated + deterministic.
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


def _lez(amount: float = 12.0, pt_share: float = 0.0) -> PolicyDSL:
    return PolicyDSL(
        id="policy_lez",
        intervention=Intervention(
            type=InterventionType.low_emission_zone,
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


# --- Levers: distinct mechanism -------------------------------------------


def test_lez_charges_only_the_noncompliant_share() -> None:
    """The LEZ per-one-way charge is scaled by the non-compliant fleet share."""
    lez = derive_levers(_lez(amount=12.0))
    charge = derive_levers(_charge(amount=12.0))
    assert charge.charge_per_one_way > 0
    # LEZ applies a fleet-expected charge = full charge × non-compliant share.
    expected = charge.charge_per_one_way * DEFAULT_SIM_PARAMS.lez_noncompliant_share
    assert lez.charge_per_one_way == expected
    assert 0 < lez.charge_per_one_way < charge.charge_per_one_way


def test_lez_cleans_the_fleet_but_a_congestion_charge_does_not() -> None:
    lez = derive_levers(_lez())
    charge = derive_levers(_charge())
    # Fleet cleanup lowers World B's CO₂ factor for the LEZ...
    assert lez.co2_factor_multiplier < 1.0
    # ...and is inert for a congestion charge (it cuts emissions only via km).
    assert charge.co2_factor_multiplier == 1.0
    # The blend sits between the clean-vehicle ratio and 1.0.
    assert DEFAULT_SIM_PARAMS.lez_clean_factor_ratio <= lez.co2_factor_multiplier < 1.0


def test_lez_emits_both_behavioural_rules() -> None:
    names = {r.name for r in derive_levers(_lez()).rules}
    assert {"lez_charge", "lez_fleet_cleanup"} <= names
    # It is NOT labelled as a flat cordon charge.
    assert "cordon_charge" not in names


# --- Model: distinct outcomes ---------------------------------------------


def test_lez_shifts_fewer_commuters_than_an_equal_congestion_charge() -> None:
    """Because only non-compliant vehicles pay, the LEZ mode shift is smaller."""
    base = compute_baseline()
    lez = compute_world_b(_lez(amount=12.0), reinvestment=False)
    charge = compute_world_b(_charge(amount=12.0), reinvestment=False)
    base_car = base.mode_share.car
    # Both reduce car mode share vs baseline...
    assert lez.mode_share.car <= base_car
    assert charge.mode_share.car < base_car
    # ...but the LEZ keeps strictly more cars on the road than the full charge.
    assert lez.mode_share.car > charge.mode_share.car


def test_lez_cuts_emissions_factor_in_world_b() -> None:
    lez = compute_world_b(_lez(), reinvestment=False)
    # The reported effective factor is below the baseline fleet factor.
    assert lez.emissions.co2_kg_per_km < DEFAULT_PARAMS.car_co2_kg_per_km


def test_lez_emissions_reflect_both_levers() -> None:
    """LEZ CO₂ = fewer km (small mode shift) × a cleaner per-km factor."""
    base = compute_baseline()
    lez = compute_world_b(_lez(), reinvestment=False)
    assert lez.emissions.daily_co2_tonnes < base.emissions.daily_co2_tonnes


# --- Guardrails: World A / non-LEZ unchanged, tags, determinism -----------


def test_non_lez_policies_keep_unit_co2_multiplier() -> None:
    for pol in (_charge(), _charge(pt_share=1.0)):
        assert derive_levers(pol).co2_factor_multiplier == 1.0


def test_charge_world_b_emissions_factor_equals_baseline() -> None:
    """A congestion charge must not change the emissions factor (regression)."""
    charge = compute_world_b(_charge(), reinvestment=False)
    assert charge.emissions.co2_kg_per_km == DEFAULT_PARAMS.car_co2_kg_per_km


def test_lez_metrics_are_simulated() -> None:
    lez = compute_world_b(_lez())
    for m in lez.metrics:
        assert m.tag == MetricTag.simulated


def test_lez_is_deterministic() -> None:
    a = compute_world_b(_lez())
    b = compute_world_b(_lez())
    assert a.model_dump() == b.model_dump()
