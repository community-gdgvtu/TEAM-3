"""Simulated media generator checks — ROADMAP M6, SPEC §15/§34.

Every artifact must be labelled SIMULATED, cite the model output it rests on,
span the archetypes at both horizons, and never reference a real outlet/byline.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.media import run_media
from app.media.schema import SIMULATED_LABEL
from app.policy.dsl import (
    Intervention,
    InterventionType,
    PolicyDSL,
    RevenueAllocation,
)

client = TestClient(app)


def _policy(amount: float = 12.0, pt_share: float = 1.0) -> PolicyDSL:
    return PolicyDSL(
        id="policy_media_test",
        intervention=Intervention(
            type=InterventionType.road_pricing, amount=amount, currency="local"
        ),
        revenue_allocation=RevenueAllocation(
            public_transport=pt_share, general_fund=1.0 - pt_share
        ),
    )


def test_two_horizons_all_archetypes() -> None:
    m = run_media(_policy())
    labels = [s.label for s in m.scenarios]
    assert labels == ["Month 5", "Year 2"]
    for s in m.scenarios:
        arche = {h.archetype for h in s.headlines}
        assert len(arche) == 6  # one per archetype, distinct


def test_every_artifact_labelled_simulated() -> None:
    m = run_media(_policy())
    assert m.disclaimer == SIMULATED_LABEL
    for s in m.scenarios:
        for h in s.headlines:
            assert h.label == SIMULATED_LABEL
            assert "SIMULATED" in h.outlet_label
            assert h.provenance == "Generated"


def test_headlines_cite_model_output() -> None:
    m = run_media(_policy())
    for s in m.scenarios:
        for h in s.headlines:
            assert h.headline and h.standfirst
            assert h.cited_refs, f"{h.archetype} cited nothing"


def test_environmental_cites_emissions_when_present() -> None:
    m = run_media(_policy())
    env = [
        h
        for s in m.scenarios
        for h in s.headlines
        if h.archetype == "environmental"
    ]
    # Emissions milestone fires for a real charge, so the green outlet cites it.
    assert any("emissions.daily_co2_tonnes" in h.cited_refs for h in env)


def test_deterministic() -> None:
    a = run_media(_policy())
    b = run_media(_policy())
    assert [h.headline for s in a.scenarios for h in s.headlines] == [
        h.headline for s in b.scenarios for h in s.headlines
    ]


def test_endpoint_contract() -> None:
    body = {
        "policy": {
            "id": "policy_ep",
            "intervention": {"type": "road_pricing", "amount": 12.0},
            "revenue_allocation": {"public_transport": 1.0, "general_fund": 0.0},
        }
    }
    r = client.post("/media", json=body)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["policy_id"] == "policy_ep"
    assert data["disclaimer"] == SIMULATED_LABEL
    assert len(data["scenarios"]) == 2
