"""Tests for the distributional microsimulation layer (SPEC §7.3)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.baseline.schema import MetricTag
from app.main import create_app
from app.microsim.model import build_microsim_report
from app.policy.dsl import (
    Intervention,
    InterventionType,
    PolicyDSL,
    RevenueAllocation,
)

app = create_app()
client = TestClient(app)


def _charge(amount: float = 12.0, pt_share: float = 1.0, exemptions=None) -> PolicyDSL:
    return PolicyDSL(
        id="ms_charge",
        intervention=Intervention(type=InterventionType.road_pricing, amount=amount),
        exemptions=exemptions or [],
        revenue_allocation=RevenueAllocation(
            public_transport=pt_share, general_fund=1.0 - pt_share
        ),
    )


def _noop() -> PolicyDSL:
    # A genuinely inert intervention: ``other`` maps to no lever, so no one is
    # charged, banned, or served better. (``transit_investment`` is no longer a
    # no-op — it now improves transit service, so it would create winners.)
    return PolicyDSL(
        id="ms_noop",
        intervention=Intervention(type=InterventionType.other),
    )


def test_endpoint_returns_report() -> None:
    res = client.post("/microsim", json={"policy": _charge().model_dump()})
    assert res.status_code == 200
    body = res.json()
    assert body["policy_id"] == "ms_charge"
    assert body["provenance"] == MetricTag.simulated.value
    assert len(body["by_income_decile"]) == 10
    assert body["not_modelled"]


def test_deterministic() -> None:
    a = build_microsim_report(_charge())
    b = build_microsim_report(_charge())
    assert a.model_dump() == b.model_dump()


def test_partition_is_complete() -> None:
    r = build_microsim_report(_charge())
    assert r.winners + r.losers + r.unaffected == r.commuters
    # Every commuter lands in exactly one decile.
    assert sum(g.agents for g in r.by_income_decile) == r.commuters


def test_charge_creates_losers_and_payers() -> None:
    r = build_microsim_report(_charge())
    assert r.losers > 0
    assert r.payers > 0
    assert r.mean_payer_burden_pct > 0


def test_reinvestment_creates_winners() -> None:
    # With revenue reinvested in transit, transit users' generalized cost falls,
    # so some commuters are strictly better off.
    reinvest = build_microsim_report(_charge(pt_share=1.0))
    assert reinvest.winners > 0
    # A general-fund charge (no reinvestment) yields no transit-driven winners.
    general_fund = build_microsim_report(_charge(pt_share=0.0))
    assert general_fund.winners < reinvest.winners


def test_flat_charge_is_regressive() -> None:
    r = build_microsim_report(_charge(pt_share=0.0))
    # Bottom-decile charge burden exceeds top-decile burden.
    assert r.regressivity_ratio > 1.0


def test_low_income_exemption_removes_bottom_burden() -> None:
    r = build_microsim_report(_charge(exemptions=["low-income"]))
    assert r.by_income_decile[0].mean_burden_pct_income == 0.0


def test_noop_policy_leaves_everyone_unaffected() -> None:
    r = build_microsim_report(_noop())
    assert r.winners == 0
    assert r.losers == 0
    assert r.unaffected == r.commuters
    assert r.payers == 0
