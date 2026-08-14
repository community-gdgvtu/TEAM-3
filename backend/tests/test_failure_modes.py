"""Failure Mode Register checks — ROADMAP M5, SPEC §12/§34.

The register must carry the SPEC §12 fields, rank by expected risk, raise the
regressive-burden mode only when no low-income exemption exists, and keep the
Estimated-scores / Simulated-evidence provenance split.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.parliament import build_failure_register, simulate_brief
from app.policy.dsl import (
    Intervention,
    InterventionType,
    PolicyDSL,
    RevenueAllocation,
)

client = TestClient(app)


def _policy(amount: float = 12.0, pt_share: float = 1.0, exemptions=None) -> PolicyDSL:
    return PolicyDSL(
        id="policy_fm_test",
        intervention=Intervention(
            type=InterventionType.road_pricing, amount=amount, currency="local"
        ),
        revenue_allocation=RevenueAllocation(
            public_transport=pt_share, general_fund=1.0 - pt_share
        ),
        exemptions=exemptions or [],
    )


def _register(policy: PolicyDSL):
    return build_failure_register(simulate_brief(policy))


def test_register_has_spec12_fields() -> None:
    reg = _register(_policy())
    assert reg.failure_modes
    for m in reg.failure_modes:
        assert m.risk and m.mechanism and m.mitigation
        assert m.severity in {"low", "medium", "high", "critical"}
        assert 0.0 <= m.probability <= 1.0
        assert m.evidence  # every mode is grounded


def test_register_ranked_by_risk_score_desc() -> None:
    reg = _register(_policy())
    scores = [m.risk_score for m in reg.failure_modes]
    assert scores == sorted(scores, reverse=True)


def test_regressive_mode_only_without_exemption() -> None:
    with_charge = _register(_policy(exemptions=[]))
    assert any(m.id == "fm_regressive_backlash" for m in with_charge.failure_modes)
    exempted = _register(_policy(exemptions=["low-income"]))
    assert all(m.id != "fm_regressive_backlash" for m in exempted.failure_modes)


def test_assumption_fragility_always_present() -> None:
    reg = _register(_policy())
    assert any(m.id == "fm_assumption_fragility" for m in reg.failure_modes)


def test_provenance_estimated_overlay() -> None:
    reg = _register(_policy())
    assert reg.provenance == "Estimated"
    # Evidence still points at Simulated model output.
    for m in reg.failure_modes:
        for e in m.evidence:
            assert e.tag == "Simulated"


def test_endpoint_contract() -> None:
    body = {
        "policy": {
            "id": "policy_ep",
            "intervention": {"type": "road_pricing", "amount": 12.0},
            "revenue_allocation": {"public_transport": 1.0, "general_fund": 0.0},
        }
    }
    r = client.post("/parliament/failure-modes", json=body)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["policy_id"] == "policy_ep"
    assert data["failure_modes"]
    assert data["failure_modes"][0]["risk_score"] >= data["failure_modes"][-1]["risk_score"]
