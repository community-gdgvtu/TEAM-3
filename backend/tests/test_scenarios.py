"""Tests for the scenario-presets catalogue (GET /scenarios).

The catalogue is the discoverable menu of canonical demo policies. The
load-bearing guarantees: (1) every card's structured DSL is the *real* compiler
output for its prompt, so it can never disagree with ``POST /policy/compile``;
(2) both advertised bodies actually drive their endpoints (a judge can copy them
straight in); (3) the library is Observed, deterministic, and never leaks a
non-§34 provenance tag; (4) it stays reconciled with the capability manifest.
"""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from app.main import app
from app.policy import compile_policy
from app.scenarios import build_library, scenario_ids

client = TestClient(app)

#: The intervention family each curated scenario must compile to (pins that the
#: prompts keep hitting the intended lever even if the compiler rules evolve).
_EXPECTED_FAMILY = {
    "congestion_charge_cbd": "road_pricing",
    "congestion_charge_general_fund": "road_pricing",
    "pedestrianise_core": "pedestrianisation",
    "low_emission_zone": "low_emission_zone",
    "workplace_parking_levy": "parking_levy",
    "bus_network_investment": "transit_investment",
}


def test_library_shape_and_provenance() -> None:
    m = client.get("/scenarios").json()
    assert m["provenance"] == "Observed"  # curated inputs → Observed about itself
    assert m["count"] == len(m["scenarios"]) == len(scenario_ids())
    assert m["count"] >= 5
    # Families list is the sorted distinct set of card families.
    assert m["families"] == sorted({c["family"] for c in m["scenarios"]})
    # A diverse menu — at least four distinct intervention families for the demo.
    assert len(m["families"]) >= 4


def test_each_card_family_matches_expectation() -> None:
    m = client.get("/scenarios").json()
    by_id = {c["id"]: c for c in m["scenarios"]}
    assert set(by_id) == set(_EXPECTED_FAMILY)
    for sid, family in _EXPECTED_FAMILY.items():
        assert by_id[sid]["family"] == family
        # Family is derived from the compiled DSL, so they must agree.
        assert by_id[sid]["compiled"]["policy"]["intervention"]["type"] == family


def test_compiled_dsl_matches_the_real_compiler() -> None:
    """A card can never disagree with POST /policy/compile for the same text."""
    for card in build_library().scenarios:
        fresh = compile_policy(card.text)
        assert card.compiled.model_dump() == fresh.model_dump()
        # The compiler structures text → DSL; that is Generated, never a number.
        assert card.compiled.provenance == "Generated"
        # simulate_body carries exactly the compiled DSL.
        assert card.simulate_body == {"policy": fresh.policy.model_dump()}
        assert card.answer_body == {
            "text": card.text,
            "objective": card.objective,
            "constraints": card.constraints,
        }


def test_bodies_actually_drive_their_endpoints() -> None:
    """Both advertised bodies are copy-paste runnable against the live engine."""
    m = client.get("/scenarios").json()
    for card in m["scenarios"]:
        sim = client.post("/simulate", json=card["simulate_body"])
        assert sim.status_code == 200, card["id"]
        assert sim.json()["provenance"]  # a §34-tagged simulation result
        ns = client.post("/north-star", json=card["answer_body"])
        assert ns.status_code == 200, card["id"]


def test_single_scenario_and_404() -> None:
    ok = client.get("/scenarios/pedestrianise_core")
    assert ok.status_code == 200
    assert ok.json()["id"] == "pedestrianise_core"

    bad = client.get("/scenarios/does_not_exist")
    assert bad.status_code == 404
    body = bad.json()
    assert body["valid_ids"] == scenario_ids()


def test_library_is_deterministic() -> None:
    a = client.get("/scenarios").json()
    b = client.get("/scenarios").json()
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def test_no_stray_provenance_tags() -> None:
    """Every `provenance` field anywhere in the payload is a valid §34 tag."""
    allowed = {"Observed", "Estimated", "Simulated", "Generated"}

    def walk(obj: object) -> None:
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k == "provenance" and isinstance(v, str):
                    assert v in allowed, v
                walk(v)
        elif isinstance(obj, list):
            for item in obj:
                walk(item)

    walk(client.get("/scenarios").json())


def test_advertised_on_root() -> None:
    assert client.get("/").json()["scenarios"] == "/scenarios"
