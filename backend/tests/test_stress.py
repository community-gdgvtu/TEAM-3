"""Tests for the stress-testing layer (SPEC §20)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app
from app.policy.dsl import (
    Intervention,
    InterventionType,
    PolicyDSL,
    RevenueAllocation,
)
from app.stress.catalogue import SHOCK_CATALOGUE, catalogue_keys, get_scenario
from app.stress.model import _metric_verdict, run_stress_test

app = create_app()
client = TestClient(app)


def _charge_policy(amount: float = 12.0, pt_share: float = 1.0) -> PolicyDSL:
    return PolicyDSL(
        id="policy_stress_test",
        intervention=Intervention(
            type=InterventionType.road_pricing, amount=amount, currency="local"
        ),
        revenue_allocation=RevenueAllocation(
            public_transport=pt_share, general_fund=1.0 - pt_share
        ),
    )


def test_catalogue_lists_all_spec20_shocks() -> None:
    res = client.get("/stress-test/catalogue")
    assert res.status_code == 200
    body = res.json()
    keys = {s["key"] for s in body["scenarios"]}
    # The eight SPEC §20 toggles must all be present.
    assert keys == {
        "recession",
        "fuel_price_spike",
        "flood",
        "heatwave",
        "population_growth",
        "migration_change",
        "technology_adoption",
        "interest_rate_shock",
    }
    # Scenario magnitudes are Estimated scenario assumptions, not observed.
    assert all(s["provenance"] == "Estimated" for s in body["scenarios"])
    # Each declares a fidelity so the result is never over-sold (SPEC §34).
    assert all(s["fidelity"] in {"modelled", "partial", "proxy"} for s in body["scenarios"])


def test_endpoint_runs_all_scenarios_by_default() -> None:
    res = client.post("/stress-test", json={"policy": _charge_policy().model_dump()})
    assert res.status_code == 200
    body = res.json()
    assert body["policy_id"] == "policy_stress_test"
    # Policy deltas are Simulated (SPEC §34).
    assert body["provenance"] == "Simulated"
    assert len(body["scenarios"]) == len(SHOCK_CATALOGUE)
    assert body["baseline"]["verdict"] == "reference"
    # Every scenario is bucketed into exactly one robustness list.
    rob = body["robustness"]
    total = len(rob["robust_to"]) + len(rob["degrades_under"]) + len(rob["fails_under"])
    assert total == len(SHOCK_CATALOGUE)


def test_shock_actually_changes_the_world() -> None:
    """A fuel-price spike must move the policy delta vs the no-shock baseline."""
    report = run_stress_test(_charge_policy(), scenario_keys=["fuel_price_spike"])
    fuel = report.scenarios[0]
    # For at least one headline metric, the shocked delta differs from baseline
    # (shocks are applied to both worlds, but they still change the levels).
    assert any(
        abs(m.delta_shocked - m.delta_baseline) > 1e-6 for m in fuel.metrics
    ), "fuel-price spike had no effect on any metric"


def test_subset_and_horizon_selection() -> None:
    res = client.post(
        "/stress-test",
        json={
            "policy": _charge_policy().model_dump(),
            "scenarios": ["recession", "fuel_price_spike"],
            "horizon_months": 24,
        },
    )
    assert res.status_code == 200
    body = res.json()
    assert [s["key"] for s in body["scenarios"]] == ["recession", "fuel_price_spike"]
    assert body["horizon_months"] == 24.0


def test_unknown_scenario_returns_404_with_valid_keys() -> None:
    res = client.post(
        "/stress-test",
        json={"policy": _charge_policy().model_dump(), "scenarios": ["asteroid"]},
    )
    assert res.status_code == 404
    detail = res.json()["detail"]
    assert "asteroid" in detail["error"]
    assert set(detail["valid_scenarios"]) == set(catalogue_keys())


def test_metric_verdict_classification() -> None:
    """The robustness classifier must span robust → reversed (SPEC §20)."""
    # intended decrease: benefit = -delta.
    assert _metric_verdict("decrease", -100.0, -100.0)[0] == "robust"
    assert _metric_verdict("decrease", -100.0, -50.0)[0] == "weakened"
    assert _metric_verdict("decrease", -100.0, -10.0)[0] == "neutralised"
    assert _metric_verdict("decrease", -100.0, 20.0)[0] == "reversed"
    assert _metric_verdict("decrease", -100.0, -130.0)[0] == "strengthened"
    # No baseline benefit → not stressed.
    verdict, retained = _metric_verdict("decrease", 0.0, 0.0)
    assert verdict == "n/a" and retained is None
    # intended increase mirrors the logic.
    assert _metric_verdict("increase", 100.0, 50.0)[0] == "weakened"
    assert _metric_verdict("increase", 100.0, 100.0)[0] == "robust"


def test_retained_pct_matches_verdict() -> None:
    report = run_stress_test(_charge_policy(), scenario_keys=["fuel_price_spike"])
    for m in report.scenarios[0].metrics:
        if m.verdict in ("robust", "weakened", "neutralised", "strengthened"):
            assert m.retained_pct is not None


def test_deterministic() -> None:
    a = run_stress_test(_charge_policy(), scenario_keys=["recession"]).model_dump()
    b = run_stress_test(_charge_policy(), scenario_keys=["recession"]).model_dump()
    assert a == b


def test_scenario_overrides_are_transparent() -> None:
    """Every scenario maps to documented Shocks knobs (SPEC §20 no hidden RNG)."""
    fuel = get_scenario("fuel_price_spike")
    assert fuel is not None
    assert fuel.overrides.car_cost_per_km_multiplier == 1.5
    # Nothing secretly random: the overrides fully determine the scenario.
    recession = get_scenario("recession")
    assert recession is not None
    assert recession.overrides.demand_growth_per_year == -0.010
