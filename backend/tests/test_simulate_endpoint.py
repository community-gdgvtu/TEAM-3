"""`POST /simulate` contract checks — ROADMAP M3, SPEC §5/§21/§34.

Verifies the endpoint returns World A, World B and Δ(B−A) across the checkpoints,
that the delta isolates the policy, that shocks hit both worlds, and that every
payload is tagged Simulated.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _pricing_body(amount: float = 12.0, pt_share: float = 1.0, **extra) -> dict:
    body = {
        "policy": {
            "id": "policy_sim_test",
            "intervention": {
                "type": "road_pricing",
                "amount": amount,
                "currency": "local",
                "geographic_zone": "cbd_polygon",
            },
            "revenue_allocation": {
                "public_transport": pt_share,
                "general_fund": 1.0 - pt_share,
            },
        }
    }
    body.update(extra)
    return body


def test_simulate_returns_all_three_worlds() -> None:
    r = client.post("/simulate", json=_pricing_body())
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["provenance"] == "Simulated"
    assert data["policy_id"] == "policy_sim_test"
    assert data["world_a"]["snapshot"]["world"] == "A"
    assert data["world_b"]["snapshot"]["world"] == "B"
    # Aligned checkpoint grids across all three.
    a_cp = [c["label"] for c in data["world_a"]["timeseries"]["checkpoints"]]
    b_cp = [c["label"] for c in data["world_b"]["timeseries"]["checkpoints"]]
    d_cp = [c["label"] for c in data["delta"]["checkpoints"]]
    assert a_cp == b_cp == d_cp
    assert len(d_cp) == 8


def test_delta_equals_b_minus_a_pointwise() -> None:
    r = client.post("/simulate", json=_pricing_body())
    data = r.json()
    for s in data["delta"]["series"]:
        for p in s["points"]:
            assert abs(p["delta"] - (p["world_b"] - p["world_a"])) < 1e-6


def test_delta_car_share_is_negative_end_state() -> None:
    # A cordon charge must reduce car mode share by the long horizon.
    r = client.post("/simulate", json=_pricing_body())
    data = r.json()
    car = next(s for s in data["delta"]["series"] if s["key"] == "mode_share.car_pct")
    assert car["points"][-1]["delta"] < 0
    # T0 delta is ~0 (no adaptation yet).
    assert abs(car["points"][0]["delta"]) < 1e-6


def test_all_metrics_tagged_simulated() -> None:
    r = client.post("/simulate", json=_pricing_body())
    data = r.json()
    for m in data["world_b"]["snapshot"]["metrics"]:
        assert m["tag"] == "Simulated"
    assert data["delta"]["provenance"] == "Simulated"
    for s in data["delta"]["series"]:
        assert s["tag"] == "Simulated"


def test_seed_is_echoed_and_deterministic() -> None:
    body = _pricing_body(seed=42)
    r1 = client.post("/simulate", json=body).json()
    r2 = client.post("/simulate", json=body).json()
    assert r1["seed"] == 42
    # Deterministic: identical payloads for the delta series.
    d1 = [p["delta"] for s in r1["delta"]["series"] for p in s["points"]]
    d2 = [p["delta"] for s in r2["delta"]["series"] for p in s["points"]]
    assert d1 == d2


def test_fuel_shock_shifts_baseline_car_share() -> None:
    # A large fuel-price shock (applied to both worlds) should push some
    # commuters off cars even in World A vs the no-shock baseline.
    base = client.post("/simulate", json=_pricing_body()).json()
    shocked = client.post(
        "/simulate",
        json=_pricing_body(shocks={"car_cost_per_km_multiplier": 4.0}),
    ).json()
    a_car_base = base["world_a"]["snapshot"]["mode_share"]["car_pct"]
    a_car_shock = shocked["world_a"]["snapshot"]["mode_share"]["car_pct"]
    assert a_car_shock < a_car_base
    assert shocked["shocks_applied"]["car_cost_per_km_multiplier"] == 4.0
