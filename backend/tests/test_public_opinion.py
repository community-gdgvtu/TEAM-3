"""Cohort opinion model checks — ROADMAP M6, SPEC §13/§34.

Distributions must be well-formed and sum to ~1, cohorts must partition the
population, a low-income exemption must raise low-income support, revenue
reinvestment must help, and everything stays deterministic + Simulated.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.opinion import compute_public_opinion
from app.policy.dsl import (
    Intervention,
    InterventionType,
    PolicyDSL,
    RevenueAllocation,
)

client = TestClient(app)


def _policy(amount: float = 12.0, pt_share: float = 1.0, exemptions=None) -> PolicyDSL:
    return PolicyDSL(
        id="policy_opinion_test",
        intervention=Intervention(
            type=InterventionType.road_pricing, amount=amount, currency="local"
        ),
        revenue_allocation=RevenueAllocation(
            public_transport=pt_share, general_fund=1.0 - pt_share
        ),
        exemptions=exemptions or [],
    )


def _dist_sum(d) -> float:
    return (
        d.strong_support + d.support + d.neutral + d.oppose + d.strong_oppose + d.uncertain
    )


def test_overall_distribution_normalised() -> None:
    op = compute_public_opinion(_policy())
    assert abs(_dist_sum(op.overall) - 1.0) < 1e-3
    assert -1.0 <= op.overall.net_support <= 1.0


def test_cohorts_partition_population() -> None:
    op = compute_public_opinion(_policy())
    assert sum(c.size for c in op.cohorts) == op.population
    for c in op.cohorts:
        assert abs(_dist_sum(c.distribution) - 1.0) < 1e-3


def test_cohorts_sorted_most_opposed_first() -> None:
    op = compute_public_opinion(_policy())
    supports = [c.mean_support for c in op.cohorts]
    assert supports == sorted(supports)


def test_low_income_exemption_raises_low_income_support() -> None:
    no_ex = compute_public_opinion(_policy(exemptions=[]))
    with_ex = compute_public_opinion(_policy(exemptions=["low-income"]))

    def low_support(op) -> float:
        lows = [c for c in op.cohorts if c.income_band in {"low", "lower-middle"}]
        n = sum(c.size for c in lows)
        return sum(c.mean_support * c.size for c in lows) / n

    assert low_support(with_ex) > low_support(no_ex)


def test_reinvestment_improves_overall_support() -> None:
    none = compute_public_opinion(_policy(pt_share=0.0))
    full = compute_public_opinion(_policy(pt_share=1.0))
    assert full.overall.net_support > none.overall.net_support


def test_deterministic() -> None:
    a = compute_public_opinion(_policy())
    b = compute_public_opinion(_policy())
    assert a.overall == b.overall


def test_provenance_simulated() -> None:
    op = compute_public_opinion(_policy())
    assert op.provenance == "Simulated"


def test_endpoint_contract() -> None:
    body = {
        "policy": {
            "id": "policy_ep",
            "intervention": {"type": "road_pricing", "amount": 12.0},
            "revenue_allocation": {"public_transport": 1.0, "general_fund": 0.0},
        }
    }
    r = client.post("/public", json=body)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["population"] > 0
    assert data["cohorts"]
    assert data["overall"]["uncertain"] >= 0
