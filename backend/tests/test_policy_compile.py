"""Tests for the policy compiler endpoint and rule-based parser (M1)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app
from app.policy.rules import parse_policy

client = TestClient(create_app())

DEMO_POLICY = (
    "Introduce a $10 congestion charge for private vehicles entering the central "
    "business district between 7:00 AM and 7:00 PM, beginning 1 January 2027. "
    "Exempt emergency vehicles and disability permit holders. Spend 70% of net "
    "proceeds on buses."
)


def test_rule_parser_extracts_demo_policy():
    policy, assumptions = parse_policy(DEMO_POLICY)
    assert policy.intervention.type.value == "road_pricing"
    assert policy.intervention.amount == 10.0
    assert policy.intervention.currency == "USD"
    assert policy.intervention.active_hours.start == "07:00"
    assert policy.intervention.active_hours.end == "19:00"
    assert policy.intervention.implementation_date == "2027-01-01"
    assert policy.intervention.geographic_zone == "cbd_polygon"
    assert "emergency_vehicle" in policy.exemptions
    assert "disability_permit" in policy.exemptions
    assert abs(policy.revenue_allocation.public_transport - 0.70) < 1e-6
    assert abs(policy.revenue_allocation.general_fund - 0.30) < 1e-6
    assert policy.stated_objectives.congestion_reduction is True
    assert policy.stated_objectives.public_transport_improvement is True
    # Every field is surfaced as a reviewable assumption.
    fields = {a.field for a in assumptions}
    assert "intervention.amount" in fields
    assert "revenue_allocation" in fields


def test_compile_endpoint_returns_dsl_and_assumptions():
    resp = client.post("/policy/compile", json={"text": DEMO_POLICY})
    assert resp.status_code == 200
    body = resp.json()
    # With no LLM key configured in tests, the deterministic path is used.
    assert body["method"] == "rule_based"
    assert body["provenance"] == "Generated"
    assert body["policy"]["intervention"]["amount"] == 10.0
    assert len(body["assumptions"]) > 0
    for a in body["assumptions"]:
        assert 0.0 <= a["confidence"] <= 1.0
        assert a["source"] in {"stated", "inferred", "default"}


def test_pedestrianisation_detected():
    policy, _ = parse_policy(
        "Pedestrianise the city centre and ban all private cars from downtown streets."
    )
    assert policy.intervention.type.value == "pedestrianisation"
    assert policy.stated_objectives.congestion_reduction is True
    assert policy.stated_objectives.emissions_reduction is True


def test_empty_text_rejected():
    resp = client.post("/policy/compile", json={"text": ""})
    assert resp.status_code == 422


def test_missing_fields_flagged_as_low_confidence_defaults():
    policy, assumptions = parse_policy("Charge cars to enter the CBD.")
    assert policy.intervention.type.value == "road_pricing"
    # No amount / date stated -> defaulted low-confidence assumptions.
    amount_assumption = next(a for a in assumptions if a.field == "intervention.amount")
    assert amount_assumption.source == "default"
    assert amount_assumption.confidence < 0.5


def test_revenue_allocation_sums_to_one():
    resp = client.post("/policy/compile", json={"text": DEMO_POLICY})
    alloc = resp.json()["policy"]["revenue_allocation"]
    total = sum(alloc.values())
    assert abs(total - 1.0) < 1e-6
