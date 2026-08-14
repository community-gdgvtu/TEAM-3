"""Baseline (World A) model checks — ROADMAP M2, SPEC §5/§8/§34.

Assertions are structural / invariant so they survive re-tuning of the
assumptions in :mod:`app.baseline.params`, plus the provenance guardrail that
every headline number is tagged Simulated (not Generated).
"""

from __future__ import annotations

from app import dataset
from app.baseline import BaselineParams, compute_baseline
from app.baseline.model import CAR, TRANSIT, WALK, choose_mode
from app.baseline.schema import MetricTag


def test_mode_share_partitions_every_commuter() -> None:
    b = compute_baseline()
    ms = b.mode_share
    assert ms.car + ms.public_transit + ms.walk == b.commuters == b.population_agents
    # Percentages sum to ~100 (rounding tolerance).
    assert abs(ms.car_pct + ms.public_transit_pct + ms.walk_pct - 100.0) <= 0.5


def test_every_agent_gets_a_valid_mode() -> None:
    valid = {CAR, TRANSIT, WALK}
    for a in dataset.population_agents():
        assert choose_mode(a) in valid


def test_choose_mode_is_deterministic() -> None:
    a = dataset.population_agents()[0]
    assert choose_mode(a) == choose_mode(a)
    assert compute_baseline().mode_share == compute_baseline().mode_share


def test_agent_without_car_never_drives() -> None:
    agent = {
        "commute_distance_km": 8.0,  # too far to walk
        "price_sensitivity": 0.5,
        "commutes_into_cbd": True,
        "car_access": False,
        "public_transit_access": True,
    }
    assert choose_mode(agent) == TRANSIT


def test_short_trip_prefers_walking_when_no_motor_edge_case() -> None:
    agent = {
        "commute_distance_km": 0.3,  # very short
        "price_sensitivity": 0.9,
        "commutes_into_cbd": False,
        "car_access": True,
        "public_transit_access": True,
    }
    # A 0.3 km trip: walking (~3.75 min) beats car/transit with their overheads.
    assert choose_mode(agent) == WALK


def test_metrics_are_tagged_simulated_not_generated() -> None:
    b = compute_baseline()
    assert b.provenance == MetricTag.simulated
    assert b.metrics, "expected headline metrics for the evidence drawer"
    for m in b.metrics:
        # Baseline numbers come from the structural model, never an LLM.
        assert m.tag == MetricTag.simulated
        assert m.tag != MetricTag.generated
        assert m.method  # provenance method string present


def test_traffic_and_emissions_are_consistent() -> None:
    b = compute_baseline()
    p = BaselineParams()
    # Emissions proxy == modelled vehicle-km × factor / 1000, within rounding.
    expected = b.traffic.daily_vehicle_km * p.car_co2_kg_per_km / 1000.0
    assert abs(b.emissions.daily_co2_tonnes - expected) < 0.05
    assert b.emissions.annual_co2_tonnes >= b.emissions.daily_co2_tonnes
    # Vehicle trips == car commuters × trips/day.
    assert b.traffic.daily_vehicle_trips == b.traffic.car_commuters * p.trips_per_commuter_per_day


def test_transit_demand_positive_and_cbd_subset() -> None:
    b = compute_baseline()
    assert b.transit.transit_commuters > 0
    # Peak CBD-bound transit trips cannot exceed all transit trips.
    assert b.transit.peak_into_cbd_transit_trips <= b.transit.daily_transit_trips


def test_params_are_exposed_for_audit() -> None:
    b = compute_baseline()
    assert "car_co2_kg_per_km" in b.params
    assert "walk_max_km" in b.params
