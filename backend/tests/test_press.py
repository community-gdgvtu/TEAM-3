"""Tests for the press conference simulation (SPEC §16/§34)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app
from app.policy.dsl import (
    Intervention,
    InterventionType,
    PolicyDSL,
    RevenueAllocation,
)
from app.press.conference import run_press_conference

app = create_app()
client = TestClient(app)


def _policy(amount: float = 12.0, pt_share: float = 1.0, exemptions=None) -> PolicyDSL:
    return PolicyDSL(
        id="policy_press_test",
        intervention=Intervention(
            type=InterventionType.road_pricing, amount=amount, currency="local"
        ),
        revenue_allocation=RevenueAllocation(
            public_transport=pt_share, general_fund=1.0 - pt_share
        ),
        exemptions=exemptions or [],
    )


def test_endpoint_returns_conference() -> None:
    res = client.post(
        "/press-conference",
        json={"policy": _policy().model_dump(), "use_llm": False},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["policy_id"] == "policy_press_test"
    assert body["method"] == "template"
    assert body["provenance"] == "Generated"
    assert "SIMULATED" in body["disclaimer"]
    assert body["opening_statement"]
    # Five archetype exchanges, all distinct lenses.
    archetypes = {ex["question"]["archetype"] for ex in body["exchanges"]}
    assert len(archetypes) == 5


def test_every_exchange_has_a_grounded_answer() -> None:
    conf = run_press_conference(_policy(), use_llm=False)
    assert len(conf.exchanges) == 5
    for ex in conf.exchanges:
        assert ex.question.question.strip()
        assert ex.answer.answer.strip()
        assert ex.answer.stance in {"defends", "acknowledges", "rebuts", "commits"}


def test_numbers_in_opening_come_from_the_model() -> None:
    """Figures quoted must match the simulated Δ, not be invented (SPEC §34)."""
    conf = run_press_conference(_policy(), use_llm=False)
    # A strong cordon charge must reduce CBD vehicle trips → cited in opening.
    assert "traffic.vehicle_trips_into_cbd" in conf.opening_refs


def test_low_income_exemption_is_reflected_in_equity_answer() -> None:
    conf = run_press_conference(
        _policy(exemptions=["low-income households"]), use_llm=False
    )
    equity = [
        ex for ex in conf.exchanges
        if ex.question.archetype.value == "opposition_local"
    ][0]
    assert "exempt" in equity.answer.answer.lower()


def test_horizon_is_snapped_to_a_checkpoint() -> None:
    conf = run_press_conference(_policy(), horizon_months=5.0, use_llm=False)
    assert conf.horizon.t_months <= 5.0
    assert conf.horizon.label
