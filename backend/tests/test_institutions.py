"""Tests for the institutional review layer (SPEC §18/§34)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.institutions.review import run_institutional_review
from app.institutions.schema import Verdict
from app.main import create_app
from app.policy.dsl import (
    Intervention,
    InterventionType,
    PolicyDSL,
    RevenueAllocation,
)

app = create_app()
client = TestClient(app)


def _policy(amount: float = 12.0, pt_share: float = 1.0, exemptions=None) -> PolicyDSL:
    return PolicyDSL(
        id="policy_inst_test",
        intervention=Intervention(
            type=InterventionType.road_pricing, amount=amount, currency="local"
        ),
        revenue_allocation=RevenueAllocation(
            public_transport=pt_share, general_fund=1.0 - pt_share
        ),
        exemptions=exemptions or [],
    )


def test_endpoint_returns_four_agents() -> None:
    res = client.post(
        "/institutions/review", json={"policy": _policy().model_dump()}
    )
    assert res.status_code == 200
    body = res.json()
    assert body["policy_id"] == "policy_inst_test"
    assert body["provenance"] == "Generated"
    agents = {r["agent"] for r in body["reviews"]}
    assert agents == {
        "Climate Agent",
        "Implementation Agent",
        "Legal/Constitutional Research Agent",
        "Auditor",
    }
    assert body["overall_verdict"] in {v.value for v in Verdict}


def test_flat_charge_without_exemption_raises_legal_concern() -> None:
    resp = run_institutional_review(_policy(exemptions=[]))
    legal = [r for r in resp.reviews if r.agent.startswith("Legal")][0]
    assert legal.verdict == Verdict.concern


def test_low_income_exemption_softens_legal_verdict() -> None:
    resp = run_institutional_review(_policy(exemptions=["low-income households"]))
    legal = [r for r in resp.reviews if r.agent.startswith("Legal")][0]
    assert legal.verdict == Verdict.conditional


def test_auditor_always_clears_on_process() -> None:
    """The audit is about evidence integrity, independent of policy strength."""
    resp = run_institutional_review(_policy(amount=0.0))
    auditor = [r for r in resp.reviews if r.agent == "Auditor"][0]
    assert auditor.verdict == Verdict.clear
    assert auditor.findings


def test_overall_verdict_is_worst_and_tally_sums() -> None:
    resp = run_institutional_review(_policy())
    assert sum(resp.verdict_tally.values()) == len(resp.reviews)
    order = {Verdict.clear: 0, Verdict.conditional: 1, Verdict.concern: 2, Verdict.block: 3}
    assert order[resp.overall_verdict] == max(order[r.verdict] for r in resp.reviews)
