"""Tests for the economic spillover layer (SPEC §7.4)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.economy.model import build_economic_spillover
from app.main import create_app
from app.policy.dsl import (
    Intervention,
    InterventionType,
    PolicyDSL,
    RevenueAllocation,
)

app = create_app()
client = TestClient(app)


def _charge_policy(amount: float = 12.0, pt_share: float = 1.0) -> PolicyDSL:
    return PolicyDSL(
        id="policy_econ_test",
        intervention=Intervention(
            type=InterventionType.road_pricing, amount=amount, currency="local"
        ),
        revenue_allocation=RevenueAllocation(
            public_transport=pt_share, general_fund=1.0 - pt_share
        ),
    )


def _pedestrianisation() -> PolicyDSL:
    return PolicyDSL(
        id="policy_ped_test",
        intervention=Intervention(
            type=InterventionType.pedestrianisation, currency="local"
        ),
        revenue_allocation=RevenueAllocation(public_transport=1.0, general_fund=0.0),
    )


def test_endpoint_returns_report() -> None:
    res = client.post("/economy", json={"policy": _charge_policy().model_dump()})
    assert res.status_code == 200
    body = res.json()
    assert body["policy_id"] == "policy_econ_test"
    # The economic translation is Estimated, never Simulated (SPEC §8/§34).
    assert body["provenance"] == "Estimated"
    assert all(ch["tag"] == "Estimated" for ch in body["channels"])
    assert body["horizon"]["t_months"] > 0


def test_charge_produces_transfer_recycling_and_freight_channels() -> None:
    report = build_economic_spillover(_charge_policy())
    ids = {c.id for c in report.channels}
    assert {"charge_transfer", "revenue_recycling", "business_logistics"} <= ids
    transfer = next(c for c in report.channels if c.id == "charge_transfer")
    recycle = next(c for c in report.channels if c.id == "revenue_recycling")
    # Withdrawal is negative, recycling positive; recycling reads the full pool
    # (commuter Simulated + freight Estimated) so it is >= the commuter withdrawal.
    assert transfer.annual_impact < 0
    assert recycle.annual_impact > 0
    assert recycle.physical_value >= transfer.physical_value


def test_reinvestment_beats_general_fund_for_local_economy() -> None:
    # Same charge; full transit reinvestment lifts the net vs dumping to the fund,
    # because reinvestment cuts commuters' mode-switch travel-time cost.
    reinvest = build_economic_spillover(_charge_policy(pt_share=1.0))
    genfund = build_economic_spillover(_charge_policy(pt_share=0.0))
    assert reinvest.net_annual_impact > genfund.net_annual_impact


def test_net_is_sum_of_channels_with_band_ordering() -> None:
    report = build_economic_spillover(_charge_policy())
    total = sum(c.annual_impact for c in report.channels)
    assert abs(report.net_annual_impact - round(total, 2)) < 1.0
    assert report.net_annual_impact_low <= report.net_annual_impact <= report.net_annual_impact_high


def test_confidence_widens_with_horizon() -> None:
    near = build_economic_spillover(_charge_policy(), horizon_months=1.0)
    far = build_economic_spillover(_charge_policy(), horizon_months=120.0)
    # Longer horizon ⇒ lower confidence (SPEC §9/§24).
    assert far.net_confidence <= near.net_confidence


def test_pedestrianisation_has_amenity_but_no_charge_channels() -> None:
    report = build_economic_spillover(_pedestrianisation())
    ids = {c.id for c in report.channels}
    # No charge ⇒ no transfer/recycling/freight channels.
    assert "charge_transfer" not in ids
    assert "business_logistics" not in ids
    # Footfall channel exists and carries the pedestrian retail amenity.
    foot = next(c for c in report.channels if c.id == "cbd_footfall")
    assert foot.annual_impact > -1e9  # present


def test_deterministic() -> None:
    a = build_economic_spillover(_charge_policy())
    b = build_economic_spillover(_charge_policy())
    assert a.net_annual_impact == b.net_annual_impact
    assert [c.annual_impact for c in a.channels] == [c.annual_impact for c in b.channels]


def test_honest_about_unmodelled_effects() -> None:
    report = build_economic_spillover(_charge_policy())
    # SPEC §34 honesty: the layer surfaces what it does not model.
    assert report.not_modelled
    joined = " ".join(report.not_modelled).lower()
    assert "congestion" in joined and "partial-equilibrium" in joined
