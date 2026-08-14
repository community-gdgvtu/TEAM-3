"""Tests for the uncertainty engine (ROADMAP M7, SPEC §24)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app
from app.policy.dsl import (
    Intervention,
    InterventionType,
    PolicyDSL,
    RevenueAllocation,
)
from app.uncertainty import run_uncertainty

app = create_app()
client = TestClient(app)


def _policy(amount: float = 12.0, pt_share: float = 1.0) -> PolicyDSL:
    return PolicyDSL(
        id="policy_uncertainty_test",
        intervention=Intervention(
            type=InterventionType.road_pricing, amount=amount, currency="local"
        ),
        revenue_allocation=RevenueAllocation(
            public_transport=pt_share, general_fund=1.0 - pt_share
        ),
    )


def _body(metric_key: str, **extra: object) -> dict:
    return {"policy": _policy().model_dump(mode="json"), "metric_key": metric_key, **extra}


def test_intervals_are_nested_and_ordered() -> None:
    res = run_uncertainty(_policy(), "traffic.daily_vehicle_km", samples=60)
    by = {i.level: i for i in res.intervals}
    assert set(by) == {50, 80, 95}
    # Wider confidence ⇒ wider band, and the median sits inside every band.
    assert by[95].high - by[95].low >= by[80].high - by[80].low >= by[50].high - by[50].low
    for lvl in (50, 80, 95):
        assert by[lvl].low <= res.median <= by[lvl].high


def test_fan_widens_with_horizon() -> None:
    res = run_uncertainty(_policy(), "transit.peak_into_cbd_transit_trips", samples=60)
    assert len(res.fan) >= 3
    first = res.fan[1]  # skip T0 (Δ≈0, zero band)
    last = res.fan[-1]

    def width95(band):
        i = next(x for x in band.intervals if x.level == 95)
        return i.high - i.low

    assert width95(last) > width95(first), "10-year fan should be wider than the near term"


def test_sensitivity_ranked_by_swing() -> None:
    res = run_uncertainty(_policy(), "traffic.daily_vehicle_km", samples=40)
    ranks = [e.rank for e in res.influential_assumptions]
    assert ranks == list(range(1, len(ranks) + 1))
    swings = [e.swing for e in res.influential_assumptions]
    assert swings == sorted(swings, reverse=True)
    # The mode-switch elasticity should be a top driver of a traffic metric.
    top_names = {e.name for e in res.influential_assumptions[:3]}
    assert "money_to_minutes" in top_names


def test_emissions_factor_dominates_emissions_metric() -> None:
    res = run_uncertainty(_policy(), "emissions.daily_co2_tonnes", samples=40)
    top = res.influential_assumptions[0]
    assert top.name == "car_co2_kg_per_km"


def test_model_disagreement_spread_nonnegative() -> None:
    res = run_uncertainty(_policy(), "transit.peak_into_cbd_transit_trips", samples=40)
    names = {v.name for v in res.model_disagreement.variants}
    assert names == {"low_response", "central", "high_response"}
    assert res.model_disagreement.spread >= 0.0


def test_deterministic_with_seed() -> None:
    a = run_uncertainty(_policy(), "mode_share.car_pct", samples=50, seed=7).model_dump()
    b = run_uncertainty(_policy(), "mode_share.car_pct", samples=50, seed=7).model_dump()
    assert a == b


def test_endpoint_contract() -> None:
    r = client.post("/uncertainty", json=_body("traffic.daily_vehicle_km", samples=40))
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["provenance"] == "Simulated"
    assert data["metric_key"] == "traffic.daily_vehicle_km"
    assert data["intervals"] and data["fan"] and data["influential_assumptions"]
    assert data["samples"] == 40


def test_unknown_metric_is_404() -> None:
    r = client.post("/uncertainty", json=_body("nope.bad", samples=40))
    assert r.status_code == 404
    assert "available_metric_keys" in r.json()["detail"]
