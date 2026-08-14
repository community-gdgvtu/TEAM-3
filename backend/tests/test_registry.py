"""Tests for the model registry / transparency manifest (SPEC §33/§34)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.baseline.params import DEFAULT_PARAMS
from app.main import create_app
from app.registry.model import build_registry
from app.simulation.timeline import DEFAULT_ADAPTATION

app = create_app()
client = TestClient(app)


def test_endpoint_returns_registry() -> None:
    res = client.get("/registry")
    assert res.status_code == 200
    body = res.json()
    assert body["app_version"]
    assert body["provenance"] == "Observed"
    assert body["models"]
    assert body["data_sources"]
    assert body["guardrails"]


def test_no_numeric_model_uses_an_llm_for_numbers() -> None:
    """SPEC §34: LLMs must never generate core numeric effects."""
    reg = build_registry()
    for m in reg.models:
        assert m.llm_touches_numbers is False, m.id
        if m.produces_numbers:
            # Numeric layers must be deterministic or seeded-stochastic, prose-free.
            assert m.determinism.startswith(("deterministic", "stochastic")), m.id
            assert m.llm_role == "none", m.id


def test_guardrails_all_hold() -> None:
    reg = build_registry()
    ids = {g.id for g in reg.guardrails}
    assert {"no_llm_numbers", "provenance_tags", "media_labelled", "widening_uncertainty"} <= ids
    assert all(g.holds for g in reg.guardrails)
    assert reg.counts["guardrails_holding"] == reg.counts["guardrails_total"]


def test_assumption_values_are_read_live_from_code() -> None:
    """The published values must match the live parameter objects, not a copy."""
    reg = build_registry()
    index = {a.name: a.value for a in reg.assumption_index}
    assert index["car_co2_kg_per_km"] == DEFAULT_PARAMS.car_co2_kg_per_km
    assert index["behaviour_tau_months"] == DEFAULT_ADAPTATION.behaviour_tau_months
    # Index is de-duplicated.
    names = [a.name for a in reg.assumption_index]
    assert len(names) == len(set(names))


def test_counts_are_consistent() -> None:
    reg = build_registry()
    c = reg.counts
    assert c["models"] == len(reg.models)
    assert c["numeric_models"] == sum(1 for m in reg.models if m.produces_numbers)
    assert c["documented_assumptions"] == len(reg.assumption_index)
    assert c["models_touching_numbers_with_llm"] == 0
