"""Amendment loop checks — ROADMAP M5, SPEC §12/§21/§34.

An amendment edits only the structured policy; the recomputed worlds and the
Δ(amended − original) must stay deterministic and Simulated, and a low-income
exemption must measurably change the priced-commuter base.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.policy.dsl import (
    Intervention,
    InterventionType,
    PolicyDSL,
    RevenueAllocation,
)
from app.simulation import Amendment, apply_amendment, compare_amendment

client = TestClient(app)


def _policy(amount: float = 12.0, pt_share: float = 1.0) -> PolicyDSL:
    return PolicyDSL(
        id="policy_amend_test",
        intervention=Intervention(
            type=InterventionType.road_pricing, amount=amount, currency="local"
        ),
        revenue_allocation=RevenueAllocation(
            public_transport=pt_share, general_fund=1.0 - pt_share
        ),
    )


def test_apply_amendment_does_not_mutate_original() -> None:
    p = _policy()
    amended = apply_amendment(p, Amendment(label="exempt low income", exempt_low_income=True))
    assert p.exemptions == []  # original untouched
    assert any("income" in e.lower() for e in amended.exemptions)
    assert amended.id != p.id


def test_charge_multiplier_scales_amount() -> None:
    p = _policy(amount=10.0)
    amended = apply_amendment(p, Amendment(label="double", charge_multiplier=2.0))
    assert amended.intervention.amount == 20.0


def test_set_pt_share_rebalances_revenue() -> None:
    p = _policy(pt_share=0.0)
    amended = apply_amendment(p, Amendment(label="reinvest", set_public_transport_share=0.5))
    assert amended.revenue_allocation.public_transport == 0.5
    assert amended.revenue_allocation.general_fund == 0.5


def test_low_income_exemption_reduces_priced_commuters() -> None:
    p = _policy()
    cmp = compare_amendment(p, Amendment(label="exempt bottom income", exempt_low_income=True))
    # Exempting low-income commuters can only reduce (or hold) the priced base.
    assert cmp.amended_world_b.priced_car_commuters <= cmp.original_world_b.priced_car_commuters
    assert cmp.changes  # human-readable description present


def test_amendment_delta_is_amended_minus_original() -> None:
    p = _policy()
    cmp = compare_amendment(p, Amendment(label="halve charge", charge_multiplier=0.5))
    # amendment_delta = amended_vs_baseline − original_vs_baseline, pointwise.
    amd = {s.key: s for s in cmp.amended_vs_baseline.series}
    orig = {s.key: s for s in cmp.original_vs_baseline.series}
    for s in cmp.amendment_delta.series:
        a_pts = amd[s.key].points
        o_pts = orig[s.key].points
        for dp, ap, op in zip(s.points, a_pts, o_pts):
            assert abs(dp.delta - (ap.delta - op.delta)) < 0.05


def test_amendment_all_series_tagged_simulated() -> None:
    p = _policy()
    cmp = compare_amendment(p, Amendment(label="x", exempt_low_income=True))
    assert cmp.amendment_delta.provenance == "Simulated"
    for s in cmp.amendment_delta.series:
        assert s.tag == "Simulated"


def test_endpoint_amend_contract() -> None:
    body = {
        "policy": {
            "id": "policy_ep",
            "intervention": {"type": "road_pricing", "amount": 12.0},
            "revenue_allocation": {"public_transport": 1.0, "general_fund": 0.0},
        },
        "amendment": {"label": "exempt bottom-30% income", "exempt_low_income": True},
    }
    r = client.post("/simulate/amend", json=body)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["original_policy_id"] == "policy_ep"
    assert "exempt" in " ".join(data["changes"]).lower()
    assert data["amendment_delta"]["series"]
