"""Tests for the Baseline World Model endpoint (SPEC §5 / §28.2)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.dataset import load_zones, population_agents
from app.main import app
from app.world import ALL_LAYERS

client = TestClient(app)

_TAGS = {"Observed", "Estimated", "Simulated", "Generated"}


def test_world_returns_all_six_layers():
    r = client.get("/world")
    assert r.status_code == 200
    d = r.json()
    assert d["world"] == "A"
    assert d["layers_returned"] == list(ALL_LAYERS)
    for layer in ALL_LAYERS:
        assert d[layer] is not None, f"missing layer {layer}"


def test_population_matches_dataset():
    d = client.get("/world").json()
    agents = population_agents()
    pop = d["population"]
    assert pop["total_agents"] == len(agents)
    assert pop["cbd_commuters"] == sum(1 for a in agents if a["commutes_into_cbd"])
    # income bands sum to the population
    assert sum(pop["income_bands"]["counts"].values()) == len(agents)
    # age bands sum to the population
    assert sum(pop["age_bands"]["counts"].values()) == len(agents)


def test_geography_matches_dataset():
    d = client.get("/world").json()
    zones = load_zones()["features"]
    geo = d["geography"]
    assert geo["zones"] == len(zones)
    assert geo["cbd_zones"] == sum(1 for f in zones if f["properties"].get("is_cbd"))
    assert geo["roads"]["links"] == 144
    assert geo["roads"]["cordon_crossing_links"] == 12


def test_income_deciles_monotonic():
    d = client.get("/world").json()
    deciles = d["population"]["income_deciles"]
    assert len(deciles) == 9
    assert deciles == sorted(deciles)


def test_environment_co2_from_baseline():
    d = client.get("/world").json()
    env = d["environment"]
    assert env["commuter_co2"]["annual_tonnes"] > 0
    # baseline daily/annual are consistent (annual ~ daily * working days)
    assert env["commuter_co2"]["daily_tonnes"] > 0
    assert env["water_present"] is True


def test_every_layer_carries_a_valid_provenance_tag():
    d = client.get("/world").json()
    assert d["provenance"] in _TAGS
    for layer in ALL_LAYERS:
        assert d[layer]["provenance"] in _TAGS


def test_layer_subset_selection():
    r = client.get("/world?layers=population,geography")
    assert r.status_code == 200
    d = r.json()
    assert d["layers_returned"] == ["population", "geography"]
    assert d["population"] is not None
    assert d["geography"] is not None
    assert d["economy"] is None
    assert d["society"] is None


def test_unknown_layer_404_lists_valid():
    r = client.get("/world?layers=population,bogus")
    assert r.status_code == 404
    for layer in ALL_LAYERS:
        assert layer in r.json()["detail"]


def test_deterministic_byte_identical():
    a = client.get("/world").content
    b = client.get("/world").content
    assert a == b


def test_institutions_and_society_are_transparency_descriptions():
    d = client.get("/world").json()
    inst = d["institutions"]
    assert "Government" in inst["parliament_agents"]
    assert len(inst["institutional_agents"]) == 4
    soc = d["society"]
    # priors are the documented small leans (low positive, upper negative)
    priors = soc["opinion_priors_by_income_band"]
    assert priors["low"] > 0 > priors["upper"]
    assert len(soc["civic_actors"]) >= 5
