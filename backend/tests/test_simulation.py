"""World-B policy simulation model checks — ROADMAP M3, SPEC §7.5/§7.7/§34.

Assertions are structural/directional so they survive re-tuning of the
assumptions in :mod:`app.simulation.levers`, plus the guardrail that every World-B
number is tagged Simulated (produced by the structural model, not an LLM).
"""

from __future__ import annotations

from app import dataset
from app.baseline import compute_baseline
from app.baseline.model import CAR, TRANSIT, WALK
from app.baseline.schema import MetricTag
from app.policy.dsl import (
    Intervention,
    InterventionType,
    PolicyDSL,
    RevenueAllocation,
)
from app.simulation import choose_mode_policy, compute_world_b, derive_levers
from app.simulation.levers import PolicyLevers


def _pricing_policy(amount: float = 12.0, pt_share: float = 1.0) -> PolicyDSL:
    return PolicyDSL(
        id="policy_test_pricing",
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


def _pedestrianisation_policy() -> PolicyDSL:
    return PolicyDSL(
        id="policy_test_ped",
        intervention=Intervention(
            type=InterventionType.pedestrianisation, geographic_zone="cbd_polygon"
        ),
        revenue_allocation=RevenueAllocation(public_transport=0.0, general_fund=1.0),
    )


def test_derive_levers_pricing_sets_charge_and_reinvestment() -> None:
    levers = derive_levers(_pricing_policy(amount=12.0, pt_share=1.0))
    # 12 daily charge amortised over 2 daily trips → 6 per one-way.
    assert levers.charge_per_one_way == 6.0
    assert not levers.car_banned_in_cbd
    # Full reinvestment → fare cheaper, transit faster.
    assert levers.transit_fare_multiplier < 1.0
    assert levers.transit_speed_multiplier > 1.0
    names = {r.name for r in levers.rules}
    assert {"cordon_charge", "transit_reinvestment"} <= names


def test_derive_levers_pedestrianisation_bans_cars() -> None:
    levers = derive_levers(_pedestrianisation_policy())
    assert levers.car_banned_in_cbd
    assert levers.charge_per_one_way == 0.0
    assert any(r.name == "pedestrianisation" for r in levers.rules)


def test_no_reinvestment_without_revenue_allocation() -> None:
    levers = derive_levers(_pricing_policy(amount=12.0, pt_share=0.0))
    assert levers.transit_fare_multiplier == 1.0
    assert levers.transit_speed_multiplier == 1.0
    assert all(r.name != "transit_reinvestment" for r in levers.rules)


def test_charge_reduces_cbd_car_traffic_vs_baseline() -> None:
    base = compute_baseline()
    wb = compute_world_b(_pricing_policy(amount=12.0, pt_share=1.0))
    # A cordon charge + better transit must not increase CBD-bound car trips.
    assert wb.traffic.vehicle_trips_into_cbd <= base.traffic.vehicle_trips_into_cbd
    # And it should pull at least some commuters onto transit.
    assert wb.transit.transit_commuters >= base.transit.transit_commuters


def test_pedestrianisation_eliminates_cbd_car_trips() -> None:
    wb = compute_world_b(_pedestrianisation_policy())
    # No car may enter a pedestrianised CBD.
    assert wb.traffic.vehicle_trips_into_cbd == 0


def test_world_b_mode_share_partitions_population() -> None:
    wb = compute_world_b(_pricing_policy())
    ms = wb.mode_share
    assert ms.car + ms.public_transit + ms.walk == wb.commuters == wb.population_agents
    assert abs(ms.car_pct + ms.public_transit_pct + ms.walk_pct - 100.0) <= 0.5


def test_world_b_is_deterministic() -> None:
    p = _pricing_policy()
    assert compute_world_b(p).mode_share == compute_world_b(p).mode_share


def test_world_b_metrics_tagged_simulated_not_generated() -> None:
    wb = compute_world_b(_pricing_policy())
    assert wb.provenance == MetricTag.simulated
    assert wb.metrics
    for m in wb.metrics:
        assert m.tag == MetricTag.simulated
        assert m.tag != MetricTag.generated
        assert m.method


def test_behavioural_rules_carry_range_and_sensitivity() -> None:
    # SPEC §7.5: each behavioural rule exposes source/parameter/range/sensitivity.
    wb = compute_world_b(_pricing_policy())
    assert wb.behavioural_rules
    for r in wb.behavioural_rules:
        assert r.parameter and r.sensitivity and r.source
        assert len(r.plausible_range) == 2


def test_priced_entries_within_cbd_car_trips() -> None:
    wb = compute_world_b(_pricing_policy(pt_share=0.0))
    # Charged entries cannot exceed all car trips into the CBD, and are positive.
    assert 0 < wb.daily_priced_entries <= wb.traffic.vehicle_trips_into_cbd


def test_exempt_agent_does_not_pay_charge() -> None:
    cbd = dataset.cbd_zone_ids()
    resident_zone = next(iter(cbd))
    levers = PolicyLevers(charge_per_one_way=6.0, exempt_residents=True)
    exempt_agent = {
        "commute_distance_km": 6.0,
        "price_sensitivity": 0.9,
        "commutes_into_cbd": True,
        "car_access": True,
        "public_transit_access": True,
        "home_zone": resident_zone,
        "income_band": "middle",
    }
    non_exempt = dict(exempt_agent, home_zone="ZZZ-not-cbd")
    # The exempt resident faces a strictly lower car generalized cost, so is at
    # least as likely to keep driving as the identical non-exempt agent.
    assert levers.is_exempt(exempt_agent, cbd)
    assert not levers.is_exempt(non_exempt, cbd)
    # Exempt agent keeps car; charged identical agent may switch away.
    assert choose_mode_policy(exempt_agent, levers, cbd) == CAR


def test_no_car_access_agent_never_drives_under_policy() -> None:
    cbd = dataset.cbd_zone_ids()
    levers = PolicyLevers(charge_per_one_way=6.0)
    agent = {
        "commute_distance_km": 8.0,
        "price_sensitivity": 0.5,
        "commutes_into_cbd": True,
        "car_access": False,
        "public_transit_access": True,
        "home_zone": "ZX",
        "income_band": "low",
    }
    assert choose_mode_policy(agent, levers, cbd) == TRANSIT
