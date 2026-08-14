"""Tests for the counterfactual comparison endpoint (ROADMAP M7, SPEC §21)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app
from app.policy.dsl import (
    Intervention,
    InterventionType,
    PolicyDSL,
    RevenueAllocation,
)
from app.simulation.amendment import Amendment
from app.simulation.counterfactual import compare_counterfactuals

app = create_app()
client = TestClient(app)


def _policy(amount: float = 12.0, pt_share: float = 1.0) -> PolicyDSL:
    return PolicyDSL(
        id="policy_compare_test",
        intervention=Intervention(
            type=InterventionType.road_pricing, amount=amount, currency="local"
        ),
        revenue_allocation=RevenueAllocation(
            public_transport=pt_share, general_fund=1.0 - pt_share
        ),
    )


def test_baseline_and_intervention_always_present() -> None:
    res = compare_counterfactuals(_policy())
    assert res.world_a is not None
    assert [w.id for w in res.worlds] == ["B"]
    assert res.worlds[0].role == "intervention"
    # SPEC §21: every headline row carries the baseline value.
    assert res.headline_table
    for row in res.headline_table:
        assert row.baseline_value is not None
        assert any(c.world_id == "B" for c in row.cells)


def test_amendments_become_worlds_c_d() -> None:
    amds = [
        Amendment(label="exempt low income", exempt_low_income=True),
        Amendment(label="half charge", charge_multiplier=0.5),
    ]
    res = compare_counterfactuals(_policy(), amds)
    assert [w.id for w in res.worlds] == ["B", "C", "D"]
    c = next(w for w in res.worlds if w.id == "C")
    assert c.role == "amendment"
    assert c.changes  # concrete edits surfaced
    # Amendment worlds carry a delta vs the intervention (B); B does not.
    assert res.worlds[0].delta_vs_intervention is None
    assert c.delta_vs_intervention is not None
    # Headline cells cover baseline + all three worlds.
    row = res.headline_table[0]
    assert {cell.world_id for cell in row.cells} == {"B", "C", "D"}


def test_low_income_exemption_changes_outcome() -> None:
    res = compare_counterfactuals(
        _policy(), [Amendment(label="exempt low income", exempt_low_income=True)]
    )
    c = next(w for w in res.worlds if w.id == "C")
    # Exempting low-income commuters should move at least one metric vs B.
    moved = any(
        abs(p.delta) > 1e-6
        for s in c.delta_vs_intervention.series
        for p in s.points
    )
    assert moved


def test_endpoint_contract() -> None:
    body = {
        "policy": _policy().model_dump(mode="json"),
        "amendments": [Amendment(label="exempt low income", exempt_low_income=True).model_dump(mode="json")],
    }
    r = client.post("/compare", json=body)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["provenance"] == "Simulated"
    assert data["world_a"]["snapshot"]["world"] == "A"
    assert [w["id"] for w in data["worlds"]] == ["B", "C"]
    assert data["headline_table"]


def test_deterministic() -> None:
    a = compare_counterfactuals(_policy(), [Amendment(label="x", charge_multiplier=0.5)]).model_dump()
    b = compare_counterfactuals(_policy(), [Amendment(label="x", charge_multiplier=0.5)]).model_dump()
    assert a == b
