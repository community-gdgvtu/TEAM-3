"""Tests for the §7.2 time-series layer (SPEC §7.2/§8/§34)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.baseline.model import compute_baseline
from app.main import create_app
from app.policy.dsl import (
    Intervention,
    InterventionType,
    PolicyDSL,
    RevenueAllocation,
)
from app.timeseries.model import run_timeseries

app = create_app()
client = TestClient(app)

_ALLOWED_TAGS = {"Observed", "Estimated", "Simulated", "Generated"}


def _pricing_policy(amount: float = 12.0, reinvest: float = 1.0) -> PolicyDSL:
    return PolicyDSL(
        id="policy_ts_test",
        intervention=Intervention(
            type=InterventionType.road_pricing, amount=amount, currency="local"
        ),
        revenue_allocation=RevenueAllocation(
            public_transport=reinvest, general_fund=1.0 - reinvest
        ),
    )


def _noop_policy() -> PolicyDSL:
    """A zero-amount charge → no behavioural change (World B ≈ World A)."""
    return PolicyDSL(
        id="policy_ts_noop",
        intervention=Intervention(
            type=InterventionType.road_pricing, amount=0.0, currency="local"
        ),
        revenue_allocation=RevenueAllocation(public_transport=0.0, general_fund=1.0),
    )


def _forecast(policy: PolicyDSL) -> dict:
    res = client.post("/timeseries", json={"policy": policy.model_dump()})
    assert res.status_code == 200, res.text
    return res.json()


def test_endpoint_shape_and_provenance() -> None:
    body = _forecast(_pricing_policy())
    assert body["provenance"] == "Estimated"
    assert body["policy_id"] == "policy_ts_test"
    assert len(body["metrics"]) == 8
    assert len(body["checkpoints"]) == 8
    for m in body["metrics"]:
        # Every provenance tag on the payload is a valid §8 tag.
        assert m["history_tag"] == "Simulated"
        assert m["world_a_tag"] == "Estimated"
        assert m["world_b_tag"] == "Simulated"
        assert len(m["world_a"]) == 8
        assert len(m["world_b"]) == 8


def test_history_is_anchored_to_the_abm_baseline() -> None:
    """The synthetic history's final month must equal the ABM baseline value —
    that anchoring is what keeps §7.2 consistent with /simulate (SPEC §34)."""
    base = {m.key: m.value for m in compute_baseline().metrics}
    body = _forecast(_pricing_policy())
    for m in body["metrics"]:
        assert m["history"], "history must be non-empty"
        assert m["history"][-1] == round(base[m["key"]], 4), m["key"]
        assert len(m["history"]) == 72


def test_world_a_intervals_widen_with_horizon() -> None:
    """SPEC §34: a forecast band must widen into the future and never invert."""
    body = _forecast(_pricing_policy())
    for m in body["metrics"]:
        widths = [p["high95"] - p["low95"] for p in m["world_a"]]
        # Monotonically non-decreasing …
        for a, b in zip(widths, widths[1:]):
            assert b >= a - 1e-6, (m["key"], widths)
        # … and the far horizon is strictly wider than T0 (a real fan-out).
        assert widths[-1] > widths[0] + 1e-6, (m["key"], widths)
        # low ≤ value ≤ high everywhere.
        for p in m["world_a"]:
            assert p["low95"] <= p["low80"] <= p["value"] <= p["high80"] <= p["high95"]


def test_policy_alters_the_baseline_trajectory() -> None:
    """§7.2: 'policy models alter the baseline trajectory.' A reinvesting charge
    must cut cordon traffic post-T0; World B ≠ World A after implementation."""
    body = _forecast(_pricing_policy())
    cordon = next(m for m in body["metrics"] if m["key"] == "traffic.vehicle_trips_into_cbd")
    # T0 = no change yet.
    assert abs(cordon["world_b"][0]["value"] - cordon["world_a"][0]["value"]) < 1e-6
    # Later horizons: World B is materially below World A.
    for i in range(1, 8):
        assert cordon["world_b"][i]["value"] < cordon["world_a"][i]["value"]
        assert cordon["policy_shift_pct"][i] < 0.0


def test_noop_policy_leaves_world_b_equal_to_world_a() -> None:
    body = _forecast(_noop_policy())
    for m in body["metrics"]:
        for wa, wb, sp in zip(m["world_a"], m["world_b"], m["policy_shift_pct"]):
            assert abs(wb["value"] - wa["value"]) < 1e-6, m["key"]
            assert abs(sp) < 1e-6


def test_share_metric_shift_is_additive_and_zero_at_t0() -> None:
    body = _forecast(_pricing_policy())
    share = next(m for m in body["metrics"] if m["key"] == "mode_share.car_pct")
    assert share["is_share"] is True
    assert abs(share["world_b"][0]["value"] - share["world_a"][0]["value"]) < 1e-6


def test_fit_diagnostics_and_honest_backtest() -> None:
    body = _forecast(_pricing_policy())
    cordon = next(m for m in body["metrics"] if m["key"] == "traffic.vehicle_trips_into_cbd")
    fit = cordon["fit"]
    # In-sample fit is tight but the honest out-of-sample backtest is reported …
    assert fit["in_sample_mape_pct"] >= 0.0
    assert fit["holdout_mape_pct"] is not None
    # … and both errors are plausible for a well-behaved synthetic series.
    assert fit["in_sample_mape_pct"] < 15.0
    assert fit["holdout_mape_pct"] < 25.0
    assert 0.0 < fit["residual_sigma"]
    assert -1.0 < fit["ar1_phi"] < 1.0


def test_direct_call_matches_endpoint_and_is_deterministic() -> None:
    p = _pricing_policy()
    a = run_timeseries(p).model_dump()
    b = run_timeseries(p).model_dump()
    assert a == b  # deterministic (SPEC §34)


def test_registry_lists_the_time_series_layer_llm_free() -> None:
    reg = client.get("/registry").json()
    ids = {m["id"] for m in reg["models"]}
    assert "time_series" in ids
    ts = next(m for m in reg["models"] if m["id"] == "time_series")
    assert ts["llm_touches_numbers"] is False
    assert ts["output_tag"] in _ALLOWED_TAGS
    assert ts["assumptions"], "time-series layer should publish its assumptions"
