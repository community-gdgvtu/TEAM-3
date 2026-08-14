"""Uncertainty-widens-with-horizon guard — the third §34 invariant, enforced globally.

SPEC §34 makes three concrete, auditable promises about the numeric core, and the
hardening layer now guards each one directly on the HTTP surface:

* **reproducible** — `test_determinism_regression.py` (same input → byte-identical output)
* **provenance-tagged / LLM-free** — `test_integration_smoke.py` (every band carries a
  tag; no registry model lets an LLM touch a number)
* **honest about the future** — *this file*: the confidence band around every forecast
  must **widen monotonically with the horizon**. A model that quotes the same ±band at
  10 years as at T0 is claiming decade-out certainty it cannot have; that is exactly the
  "AI astrology" §34 exists to forbid. Individual layers (`timeline`, `ensemble`) test
  their own widening, but nothing guards the property *across the whole forecast surface*
  the UI actually plots — so a refactor that flattens the band on one series slips
  through. This test walks the core `/simulate` and `/simulate/amend` responses and
  enforces the invariant on **every** time-series it can find, wherever it lives in the
  payload.

Pure test-track addition — no `backend/app/**` behaviour is changed.
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

# Small absolute tolerance so exactly-equal float bands (a legitimately flat baseline
# segment) never trip a "strictly less" comparison from reduction-order noise.
_EPS = 1e-9


def _demo_policy() -> dict[str, Any]:
    r = client.post("/policy/compile", json={"text": _DEMO_TEXT})
    assert r.status_code == 200, r.text
    return r.json()["policy"]


DEMO_POLICY = _demo_policy()


def _is_band_point(o: Any) -> bool:
    """A forecast point on the Time-Machine axis: a horizon plus a [low, high] band."""
    return (
        isinstance(o, dict)
        and "t_months" in o
        and "low" in o
        and "high" in o
        and all(isinstance(o.get(k), (int, float)) for k in ("t_months", "low", "high"))
    )


def _find_band_series(obj: Any, path: str = "") -> list[tuple[str, list[dict[str, Any]]]]:
    """Recursively locate every list that is entirely forecast band-points.

    Returns (json_path, points) so a failure names exactly which series broke, no
    matter how deeply the layer nests it (world_a / world_b / delta / amended / …).
    """
    found: list[tuple[str, list[dict[str, Any]]]] = []
    if isinstance(obj, list):
        if obj and all(_is_band_point(x) for x in obj):
            found.append((path, obj))
        else:
            for i, item in enumerate(obj):
                found.extend(_find_band_series(item, f"{path}[{i}]"))
    elif isinstance(obj, dict):
        for key, val in obj.items():
            found.extend(_find_band_series(val, f"{path}/{key}"))
    return found


def _band_series_for(route: str, body: dict[str, Any]) -> list[tuple[str, list[dict[str, Any]]]]:
    r = client.post(route, json=body)
    assert r.status_code == 200, f"POST {route} → {r.status_code}: {r.text}"
    series = _find_band_series(r.json())
    assert series, f"{route} exposed no forecast band-series to guard — payload shape changed?"
    return series


_SIMULATE_BODY = {"policy": DEMO_POLICY}
_AMEND_BODY = {
    "policy": DEMO_POLICY,
    "amendment": {"label": "exempt low income", "exempt_low_income": True},
}


def test_bands_never_narrow_with_horizon() -> None:
    """The core invariant: band width is non-decreasing as the horizon grows.

    Checked on both the base forecast and an amended forecast (the parliament loop
    plots the amended world too), across every band-series in each payload.
    """
    for route, body in (("/simulate", _SIMULATE_BODY), ("/simulate/amend", _AMEND_BODY)):
        for path, points in _band_series_for(route, body):
            ordered = sorted(points, key=lambda p: p["t_months"])
            widths = [p["high"] - p["low"] for p in ordered]
            for i in range(len(widths) - 1):
                assert widths[i + 1] >= widths[i] - _EPS, (
                    f"{route}{path}: confidence band NARROWS from t={ordered[i]['t_months']}mo "
                    f"(±{widths[i]:.4f}) to t={ordered[i + 1]['t_months']}mo (±{widths[i + 1]:.4f}) "
                    f"— violates SPEC §34 (uncertainty must widen with the horizon)"
                )


def test_long_horizon_band_is_strictly_wider_than_t0() -> None:
    """Guards against the *degenerate* pass: monotonicity is satisfied by a flat band too.

    The demo's whole credibility rests on the fan chart actually fanning out, so require
    that at least the far horizon is genuinely wider than T0 for the base `/simulate`
    forecast — and that this holds for *every* series, not just on average.
    """
    for path, points in _band_series_for("/simulate", _SIMULATE_BODY):
        ordered = sorted(points, key=lambda p: p["t_months"])
        w_first = ordered[0]["high"] - ordered[0]["low"]
        w_last = ordered[-1]["high"] - ordered[-1]["low"]
        assert w_last > w_first + _EPS, (
            f"/simulate{path}: band did not widen at all over the horizon "
            f"(T0 ±{w_first:.4f} vs {ordered[-1]['t_months']:.0f}mo ±{w_last:.4f}) "
            f"— a flat band claims certainty §34 forbids"
        )


def test_every_band_contains_its_central_estimate() -> None:
    """A band that excludes its own point estimate is incoherent — guard it everywhere.

    low ≤ value ≤ high must hold for every forecast point on both surfaces; a violation
    means the plotted line would fall outside its own shaded interval.
    """
    for route, body in (("/simulate", _SIMULATE_BODY), ("/simulate/amend", _AMEND_BODY)):
        for path, points in _band_series_for(route, body):
            for p in points:
                assert p["low"] <= p["high"] + _EPS, (
                    f"{route}{path} @t={p['t_months']}mo: low {p['low']} > high {p['high']}"
                )
                if "value" in p and isinstance(p["value"], (int, float)):
                    assert p["low"] - _EPS <= p["value"] <= p["high"] + _EPS, (
                        f"{route}{path} @t={p['t_months']}mo: central estimate {p['value']} "
                        f"falls outside its band [{p['low']}, {p['high']}]"
                    )
