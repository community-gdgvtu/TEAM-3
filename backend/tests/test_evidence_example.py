"""Keyless ``GET /evidence/example`` — the §26 Explainability causal trace with
no request body (SPEC §26/§34).

Every other headline surface already exposes a keyless GET example a judge can
hit with no body (``/compare/example``, ``/brief/example``, ``/run/example``,
``/north-star/example``, ``/backtest/example``). This pins the same surface for
the Evidence Drawer — the "click any output → walk the causal trace down to the
evidence" view SPEC §26 is built around — and proves it can never drift from the
real ``POST /evidence`` endpoint.
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
_DEMO_METRIC = "transit.peak_into_cbd_transit_trips"


def test_example_serves_the_full_causal_ladder_with_provenance():
    """No body → the §26 input-data→…→result ladder, every number Simulated."""
    res = client.get("/evidence/example")
    assert res.status_code == 200
    body = res.json()

    # It traces the canonical §26 metric.
    assert body["metric_key"] == _DEMO_METRIC
    # The whole trace is deterministic-model output (SPEC §34).
    assert body["provenance"] == "Simulated"
    # Ladder runs from raw inputs to the result (SPEC §26).
    stages = [s["stage"] for s in body["chain"]]
    assert stages[0] == "input-data"
    assert stages[-1] == "result"
    assert "model" in stages
    # The result node carries World A, World B and the isolated Δ.
    assert body["result"]["delta"] == (
        body["result"]["world_b"] - body["result"]["world_a"]
    )
    # The renderable §26 text ladder is present.
    assert body["ascii_trace"]


def test_example_is_byte_identical_to_the_post_endpoint():
    """The keyless example can never disagree with ``POST /evidence``."""
    policy = compile_policy(_DEMO_TEXT).policy
    posted = client.post(
        "/evidence",
        json={"policy": policy.model_dump(mode="json"), "metric_key": _DEMO_METRIC},
    )
    assert posted.status_code == 200
    example = client.get("/evidence/example")
    assert example.status_code == 200
    assert json.dumps(example.json(), sort_keys=True) == json.dumps(
        posted.json(), sort_keys=True
    )


def test_example_is_deterministic_across_two_calls():
    """Two identical keyless calls → byte-identical payloads (SPEC §34)."""
    a = client.get("/evidence/example").json()
    b = client.get("/evidence/example").json()
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)
