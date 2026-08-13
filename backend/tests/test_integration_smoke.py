"""Full-pipeline integration smoke test — guards the demo end-to-end.

Unit tests exercise each layer in isolation. This test drives the *whole engine*
through its HTTP surface exactly as the UI does: it compiles the demo policy once
(NL → DSL, SPEC §3), then feeds that single compiled DSL into every route and
asserts each returns 200. Its real job is to catch **cross-layer contract drift**
— the failure mode unit tests miss — where a shared schema change (the Policy DSL,
``Shocks``, a metric key) silently breaks a downstream endpoint that another test
file never re-runs against the live app.

It also enforces the SPEC §34 guardrails *globally*, across every response at once:

* every field literally named ``provenance`` carries one of the four allowed tags
  (Observed / Estimated / Simulated / Generated) — nothing untagged slips through;
* the core numeric sim (``/simulate``) is tagged Simulated and its Δ isolates B−A;
* the compiler output is tagged Generated (machine-structured user text);
* every model in the registry asserts ``llm_touches_numbers == False`` (no LLM in
  the numeric path);
* generated media carries the mandatory SIMULATED banner.

If any single endpoint 500s or drops its provenance tag, this one test fails —
which is what you want the night before a demo.
"""

from __future__ import annotations

from typing import Any, Iterator

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

# The SPEC §28 demo policy, as natural language — compiled once, reused everywhere.
DEMO_POLICY_TEXT = (
    "Introduce a $12 congestion charge for private vehicles entering the central "
    "business district between 7:00 AM and 7:00 PM, beginning 1 January 2027. "
    "Exempt emergency vehicles and disability permit holders. Reinvest 100% of net "
    "proceeds into buses."
)

ALLOWED_TAGS = {"Observed", "Estimated", "Simulated", "Generated"}


def _compile_demo() -> dict[str, Any]:
    """NL → Policy DSL via the real compiler endpoint (rule-based fallback if no LLM)."""
    r = client.post("/policy/compile", json={"text": DEMO_POLICY_TEXT})
    assert r.status_code == 200, r.text
    body = r.json()
    # The compiler output itself is machine-Generated structuring of user text (§34).
    assert body["provenance"] == "Generated"
    return body["policy"]


DEMO_POLICY = _compile_demo()


def _iter_provenance(obj: Any) -> Iterator[str]:
    """Yield every value stored under a ``provenance`` key, at any depth."""
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key == "provenance" and isinstance(value, str):
                yield value
            yield from _iter_provenance(value)
    elif isinstance(obj, list):
        for item in obj:
            yield from _iter_provenance(item)


def _assert_tags_valid(payload: Any, route: str) -> None:
    """Every ``provenance`` value must reference at least one allowed §34 tag.

    Some layers use ``provenance`` as a bare enum ("Simulated"); others as a
    descriptive sentence that embeds the tags ("ABM anchors Simulated; dynamics
    coefficients Estimated"). Both are legitimate — what §34 forbids is an
    untagged / empty provenance, which this catches.
    """
    for value in _iter_provenance(payload):
        assert any(tag in value for tag in ALLOWED_TAGS), (
            f"{route}: provenance {value!r} references no §34 tag "
            f"({', '.join(sorted(ALLOWED_TAGS))})"
        )


# --- Every route the engine exposes, with a minimal valid body. --------------

GET_ROUTES = [
    "/health",
    "/baseline",
    "/registry",
    "/data-fabric",
    "/backtest/example",
    "/stress-test/catalogue",
]

# Endpoints that take the compiled Policy DSL as ``policy`` (plus optional extras).
_P = {"policy": DEMO_POLICY}
POST_ROUTES: list[tuple[str, dict[str, Any]]] = [
    ("/run", _P),  # scenario orchestrator: composes the whole pipeline (§28/§29)
    ("/simulate", _P),
    ("/simulate/amend", {**_P, "amendment": {"label": "exempt low income", "exempt_low_income": True}}),
    ("/compare", {**_P, "amendments": [{"label": "halve charge", "charge_multiplier": 0.5}]}),
    ("/diffusion", {**_P, "rounds": 6}),
    ("/dynamics", _P),
    ("/economy", _P),
    ("/ensemble", _P),
    ("/evidence", {**_P, "metric_key": "traffic.vehicle_trips_into_cbd"}),
    ("/institutions/review", _P),
    ("/media", _P),
    ("/microsim", _P),
    ("/parliament/debate", _P),
    ("/parliament/failure-modes", _P),
    ("/press-conference", _P),
    ("/public", _P),
    ("/reproduce", _P),
    ("/sdg", _P),
    ("/spatial", _P),
    ("/timeseries", _P),
    ("/stress-test", {**_P, "scenarios": ["recession", "fuel_price_spike"]}),
    ("/uncertainty", {**_P, "metric_key": "traffic.daily_vehicle_km", "samples": 20}),
    ("/optimise", {
        "objective": {"reduce_transport_emissions_pct": 15},
        "constraints": {"max_average_commute_increase_pct": 12, "max_budget": 120_000_000},
    }),
    ("/backtest", {}),  # defaults to the built-in benchmark case
]


def test_all_get_routes_ok_and_tagged() -> None:
    for route in GET_ROUTES:
        r = client.get(route)
        assert r.status_code == 200, f"GET {route} → {r.status_code}: {r.text}"
        _assert_tags_valid(r.json(), f"GET {route}")


def test_all_post_routes_ok_and_tagged() -> None:
    for route, body in POST_ROUTES:
        r = client.post(route, json=body)
        assert r.status_code == 200, f"POST {route} → {r.status_code}: {r.text}"
        _assert_tags_valid(r.json(), f"POST {route}")


def test_core_simulate_is_simulated_and_delta_isolates_policy() -> None:
    data = client.post("/simulate", json=_P).json()
    assert data["provenance"] == "Simulated"
    # Δ = World B − World A, pointwise, across every checkpoint (SPEC §21).
    for series in data["delta"]["series"]:
        for point in series["points"]:
            assert abs(point["delta"] - (point["world_b"] - point["world_a"])) < 1e-6


def test_registry_asserts_no_llm_in_numeric_path() -> None:
    models = client.get("/registry").json()["models"]
    assert models, "registry should list forecast layers"
    for model in models:
        assert model["llm_touches_numbers"] is False, (
            f"{model.get('name')} claims an LLM touches numbers (violates SPEC §34)"
        )


def test_generated_media_carries_simulated_banner() -> None:
    data = client.post("/media", json=_P).json()
    blob = str(data)
    assert "SIMULATED" in blob, "media artifacts must be labelled SIMULATED (SPEC §15/§34)"
