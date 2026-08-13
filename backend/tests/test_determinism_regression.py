"""Determinism regression — the concrete anti-"AI astrology" guarantee (SPEC §34).

SPEC §34's central claim is that the numeric core is deterministic and LLM-free:
the same inputs must always produce the same numbers, so a forecast is a model
output you can audit and reproduce — not a plausible-sounding one-off. `/reproduce`
(§32) *asserts* this for a single run by re-hashing; this test *enforces* it across
the numeric HTTP surface directly: it calls each numeric endpoint **twice with an
identical body** and requires **byte-identical JSON**.

That is a stronger, sneakier guard than "returns 200" — it catches any hidden
non-determinism that would erode the core credibility claim: an unseeded RNG, a
dict/set iteration order leaking into output, wall-clock time bleeding into a
number, floating-point reduction order drift. The LLM-prose layers (`/media`,
`/press-conference`, `/parliament/debate`) are deliberately excluded — their prose
is Generated and may vary by design; their numbers are covered where they feed the
deterministic layers above.
"""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

_DEMO_TEXT = (
    "Introduce a $12 congestion charge for private vehicles entering the central "
    "business district. Reinvest 100% of net proceeds into buses."
)


def _demo_policy() -> dict[str, Any]:
    r = client.post("/policy/compile", json={"text": _DEMO_TEXT})
    assert r.status_code == 200, r.text
    return r.json()["policy"]


DEMO_POLICY = _demo_policy()
_P = {"policy": DEMO_POLICY}

# Numeric layers whose entire JSON output must be reproducible byte-for-byte.
DETERMINISTIC_ROUTES: list[tuple[str, dict[str, Any]]] = [
    ("/simulate", _P),
    ("/spatial", _P),
    ("/timeseries", _P),
    ("/microsim", _P),
    ("/citizen", _P),
    ("/economy", _P),
    ("/dynamics", _P),
    ("/sdg", _P),
    ("/ensemble", _P),
    ("/stress-test", {**_P, "scenarios": ["recession", "fuel_price_spike"]}),
    ("/diffusion", {**_P, "rounds": 6}),
    ("/public", _P),
    ("/parliament/failure-modes", _P),
    ("/uncertainty", {**_P, "metric_key": "traffic.daily_vehicle_km", "samples": 40, "seed": 7}),
]


def test_numeric_endpoints_are_byte_reproducible() -> None:
    for route, body in DETERMINISTIC_ROUTES:
        first = client.post(route, json=body)
        second = client.post(route, json=body)
        assert first.status_code == 200, f"POST {route} → {first.status_code}: {first.text}"
        assert first.text == second.text, (
            f"{route} is non-deterministic — identical input produced different output "
            f"(violates SPEC §34; the numeric core must be reproducible)"
        )


def test_monte_carlo_uncertainty_is_reproducible_by_seed() -> None:
    """The one stochastic layer must still be exactly reproducible for a fixed seed."""
    body = {**_P, "metric_key": "traffic.daily_vehicle_km", "samples": 60, "seed": 123}
    a = client.post("/uncertainty", json=body).text
    b = client.post("/uncertainty", json=body).text
    assert a == b, "seeded Monte-Carlo uncertainty must be reproducible (SPEC §24/§34)"
