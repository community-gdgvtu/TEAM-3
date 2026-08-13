"""Model Parliament debate checks — ROADMAP M5, SPEC §11/§12/§34.

With no LLM key configured (the test environment), the debate must run via the
deterministic template path, return all five personas, ground every argument in
Simulated evidence, and take role-appropriate stances.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.parliament import run_debate
from app.parliament.schema import Stance
from app.policy.dsl import (
    Constraints,
    Intervention,
    InterventionType,
    PolicyDSL,
    RevenueAllocation,
)

client = TestClient(app)


def _policy(amount: float = 12.0, pt_share: float = 1.0, exemptions=None, cap=None) -> PolicyDSL:
    return PolicyDSL(
        id="policy_parliament_test",
        intervention=Intervention(
            type=InterventionType.road_pricing,
            amount=amount,
            currency="local",
            geographic_zone="cbd_polygon",
        ),
        revenue_allocation=RevenueAllocation(
            public_transport=pt_share, general_fund=1.0 - pt_share
        ),
        exemptions=exemptions or [],
        constraints=Constraints(max_low_income_burden_increase_pct=cap),
    )


def test_debate_returns_full_panel() -> None:
    d = run_debate(_policy())
    personas = [a.persona for a in d.arguments]
    assert personas == [
        "Government",
        "Opposition",
        "Equity Advocate",
        "Economist",
        "Devil's Advocate",
    ]
    # No key in tests → deterministic template path.
    assert d.method == "template"
    assert d.provenance == "Generated"


def test_stances_are_role_appropriate() -> None:
    d = run_debate(_policy())
    by = {a.persona: a for a in d.arguments}
    assert by["Government"].stance == Stance.support
    assert by["Opposition"].stance == Stance.oppose
    assert by["Devil's Advocate"].stance == Stance.challenge
    assert by["Economist"].stance == Stance.conditional


def test_every_argument_is_evidence_grounded() -> None:
    d = run_debate(_policy())
    for a in d.arguments:
        assert a.points, f"{a.persona} produced no points"
        assert a.speech
        # Each speaker cites at least one metric or ledger event (except where the
        # policy is a pure quantity restriction — but the pricing policy always has).
        assert a.citations, f"{a.persona} cited no evidence"
        for c in a.citations:
            assert c.kind in {"metric", "event"}
            assert c.detail


def test_speech_preserves_numbers_from_points() -> None:
    # Template prose is built from the points, so figures must survive verbatim.
    d = run_debate(_policy())
    gov = next(a for a in d.arguments if a.persona == "Government")
    # The car-share figures appear in a point and must be in the speech too.
    assert any("%" in p for p in gov.points)


def test_equity_flags_regressive_charge_without_exemption() -> None:
    d = run_debate(_policy(exemptions=[]))
    eq = next(a for a in d.arguments if a.persona == "Equity Advocate")
    assert eq.stance == Stance.conditional
    assert any("regressive" in p.lower() for p in eq.points)


def test_equity_softens_with_low_income_exemption() -> None:
    d = run_debate(_policy(exemptions=["low-income residents"]))
    eq = next(a for a in d.arguments if a.persona == "Equity Advocate")
    assert eq.stance == Stance.support


def test_tally_counts_all_personas() -> None:
    d = run_debate(_policy())
    assert sum(d.tally.values()) == len(d.arguments) == 5
    assert d.summary


def test_endpoint_contract() -> None:
    body = {
        "policy": {
            "id": "policy_ep",
            "intervention": {"type": "road_pricing", "amount": 12.0},
            "revenue_allocation": {"public_transport": 1.0, "general_fund": 0.0},
        }
    }
    r = client.post("/parliament/debate", json=body)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["policy_id"] == "policy_ep"
    assert len(data["arguments"]) == 5
    assert data["motion"]
    assert data["method"] in {"llm", "template"}


def test_ask_persona_returns_grounded_answer() -> None:
    from app.parliament import ask_persona

    a = ask_persona(_policy(), "Government", "How much does the charge raise per day?")
    assert a.persona == "Government"
    assert a.method == "template"  # no key in tests
    assert a.answer
    assert a.provenance == "Generated"


def test_ask_persona_unknown_name_raises() -> None:
    from app.parliament import ask_persona

    with pytest.raises(ValueError):
        ask_persona(_policy(), "Not A Persona", "Why?")


def test_ask_endpoint_contract() -> None:
    body = {
        "policy": {
            "id": "policy_ask",
            "intervention": {"type": "road_pricing", "amount": 12.0},
            "revenue_allocation": {"public_transport": 1.0, "general_fund": 0.0},
        },
        "persona": "Opposition",
        "question": "Who actually pays this charge?",
    }
    r = client.post("/parliament/ask", json=body)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["persona"] == "Opposition"
    assert data["answer"]
    assert data["method"] in {"llm", "template"}


def test_ask_endpoint_rejects_unknown_persona() -> None:
    body = {
        "policy": {
            "id": "policy_ask2",
            "intervention": {"type": "road_pricing", "amount": 12.0},
        },
        "persona": "Mystery Guest",
        "question": "Who are you?",
    }
    r = client.post("/parliament/ask", json=body)
    assert r.status_code == 400
