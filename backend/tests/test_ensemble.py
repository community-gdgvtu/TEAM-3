"""Tests for the ensemble forecast (SPEC §8/§34)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.ensemble.model import run_ensemble
from app.main import create_app
from app.policy.dsl import (
    Intervention,
    InterventionType,
    PolicyDSL,
    RevenueAllocation,
)

app = create_app()
client = TestClient(app)


def _pricing_policy(amount: float = 12.0) -> PolicyDSL:
    return PolicyDSL(
        id="policy_ensemble_test",
        intervention=Intervention(
            type=InterventionType.road_pricing, amount=amount, currency="local"
        ),
        revenue_allocation=RevenueAllocation(public_transport=1.0, general_fund=0.0),
    )


def _ban_policy() -> PolicyDSL:
    return PolicyDSL(
        id="policy_ban_test",
        intervention=Intervention(type=InterventionType.pedestrianisation),
        revenue_allocation=RevenueAllocation(public_transport=1.0, general_fund=0.0),
    )


def test_endpoint_returns_three_methods() -> None:
    res = client.post(
        "/ensemble",
        json={"policy": _pricing_policy().model_dump(), "horizon_months": 24.0},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["policy_id"] == "policy_ensemble_test"
    assert body["provenance"] == "Estimated"
    metric = body["metrics"][0]
    ids = {m["method_id"] for m in metric["methods"]}
    assert ids == {"structural_abm", "historical_analogue", "reduced_form"}


def test_all_percentages_are_physically_valid() -> None:
    """Reductions cannot exceed 100% or be positive (a charge won't raise trips)."""
    f = run_ensemble(_pricing_policy(), horizon_months=24.0)
    m = f.metrics[0]
    for me in m.methods:
        for v in (me.central_pct, me.low_pct, me.high_pct):
            assert -100.0 <= v <= 0.0, (me.method_id, v)
    for v in (m.ensemble_central_pct, m.ensemble_low_pct, m.ensemble_high_pct):
        assert -100.0 <= v <= 0.0, v
    assert m.ensemble_low_pct <= m.ensemble_high_pct


def test_ensemble_central_is_weighted_blend() -> None:
    f = run_ensemble(_pricing_policy(), horizon_months=24.0)
    m = f.metrics[0]
    applic = [me for me in m.methods if me.applicable]
    wsum = sum(me.weight for me in applic)
    expected = sum(me.central_pct * me.weight for me in applic) / wsum
    assert abs(m.ensemble_central_pct - round(expected, 2)) < 0.05


def test_disagreement_signal_present() -> None:
    f = run_ensemble(_pricing_policy(), horizon_months=24.0)
    m = f.metrics[0]
    assert m.disagreement in {"low", "moderate", "high"}
    assert m.method_spread_pct >= 0.0
    assert m.interpretation


def test_car_ban_only_structural_applies() -> None:
    """A pure car ban has no charge → analogue/reduced-form are not applicable."""
    f = run_ensemble(_ban_policy(), horizon_months=24.0)
    m = f.metrics[0]
    applic = {me.method_id for me in m.methods if me.applicable}
    assert applic == {"structural_abm"}
    # Single applicable method → band reflects its own range, still valid.
    assert -100.0 <= m.ensemble_central_pct <= 0.0
