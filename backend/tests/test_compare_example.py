"""Keyless ``GET /compare/example`` — the §21 four-world A/B/C/D comparison
with no request body (SPEC §21/§22/§34).

Every other headline composed endpoint already exposes a keyless GET example a
judge can hit with no body (``/brief/example``, ``/run/example``,
``/north-star/example``, ``/backtest/example``). This pins the same surface for
the counterfactual comparison — arguably the most fundamental §21 view ("never
show intervention metrics without the baseline") — and proves it can never drift
from the real ``POST /compare/grand`` endpoint.
"""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from app.main import create_app
from app.policy import compile_policy

client = TestClient(create_app())

_DEMO_TEXT = (
    "Introduce a $12 congestion charge for private vehicles entering the central "
    "business district between 7:00 AM and 7:00 PM, beginning 1 January 2027. "
    "Exempt emergency vehicles and disability permit holders. Reinvest 100% of net "
    "proceeds into buses."
)


def test_example_serves_the_four_worlds_with_baseline_and_provenance():
    """No body → World A baseline + Worlds B/C/D, every number Simulated."""
    res = client.get("/compare/example")
    assert res.status_code == 200
    body = res.json()

    # Baseline is always present (SPEC §21 — never show intervention without it).
    assert body["world_a"] is not None
    # The three intervention worlds by canonical §21/§22 role.
    roles = {w["id"]: w["role"] for w in body["worlds"]}
    assert roles == {
        "B": "intervention",
        "C": "opposition_amendment",
        "D": "optimised",
    }
    # Every metric is deterministic-model output (SPEC §34).
    assert body["provenance"] == "Simulated"
    # Each headline row quotes the baseline and one cell per world.
    assert body["headline_table"]
    for row in body["headline_table"]:
        assert row["baseline_value"] is not None
        assert {c["world_id"] for c in row["cells"]} == {"B", "C", "D"}


def test_example_is_byte_identical_to_the_post_endpoint():
    """The keyless example can never disagree with ``POST /compare/grand``."""
    policy = compile_policy(_DEMO_TEXT).policy
    posted = client.post(
        "/compare/grand",
        json={
            "policy": policy.model_dump(mode="json"),
            "objective": {"reduce_transport_emissions_pct": 20},
            "constraints": {"max_low_income_burden_increase_pct": 2},
        },
    )
    assert posted.status_code == 200
    example = client.get("/compare/example")
    assert example.status_code == 200
    assert json.dumps(example.json(), sort_keys=True) == json.dumps(
        posted.json(), sort_keys=True
    )


def test_example_is_deterministic_across_two_calls():
    """Two identical keyless calls → byte-identical payloads (SPEC §34)."""
    a = client.get("/compare/example").json()
    b = client.get("/compare/example").json()
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)
