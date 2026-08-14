"""Tests for the change-assumptions-and-rerun layer (SPEC §34.10)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.assumptions import list_assumptions, rerun_with_assumptions
from app.assumptions.service import UnknownAssumption
from app.main import create_app
from app.policy.dsl import (
    Intervention,
    InterventionType,
    PolicyDSL,
    RevenueAllocation,
)

app = create_app()
client = TestClient(app)


def _policy(amount: float = 12.0, pt_share: float = 1.0) -> PolicyDSL:
    return PolicyDSL(
        id="policy_assumptions_test",
        intervention=Intervention(
            type=InterventionType.road_pricing, amount=amount, currency="local"
        ),
        revenue_allocation=RevenueAllocation(
            public_transport=pt_share, general_fund=1.0 - pt_share
        ),
    )


def _rerun_body(overrides: dict, **extra: object) -> dict:
    return {"policy": _policy().model_dump(mode="json"), "overrides": overrides, **extra}


# --- Catalogue --------------------------------------------------------------


def test_catalogue_matches_uncertainty_sweep() -> None:
    """The overridable knobs are exactly the §24-swept assumptions (no drift)."""
    from app.uncertainty.engine import ASSUMPTIONS

    res = client.get("/assumptions")
    assert res.status_code == 200
    body = res.json()
    names = {c["name"] for c in body["assumptions"]}
    assert names == {a.name for a in ASSUMPTIONS}
    assert body["count"] == len(ASSUMPTIONS)


def test_catalogue_defaults_are_live_from_code() -> None:
    """Card defaults read straight from the running dataclasses."""
    from app.baseline.params import DEFAULT_PARAMS

    cards = {c.name: c for c in list_assumptions()}
    assert cards["money_to_minutes"].default == DEFAULT_PARAMS.money_to_minutes
    for c in cards.values():
        assert c.low <= c.default <= c.high


# --- Rerun contract ---------------------------------------------------------


def test_empty_overrides_reproduce_default_delta() -> None:
    """No overrides ⇒ overridden Δ equals the default Δ everywhere (shift 0)."""
    res = rerun_with_assumptions(_policy(), {})
    for c in res.contrast:
        assert c.default_delta == c.overridden_delta
        assert abs(c.shift) < 1e-9


def test_override_moves_the_headline() -> None:
    """Pinning the mode-switch elasticity to its high end shifts the traffic Δ."""
    default = rerun_with_assumptions(_policy(), {})
    high = rerun_with_assumptions(_policy(), {"money_to_minutes": 12.0})

    key = "traffic.daily_vehicle_km"
    d0 = next(c for c in default.contrast if c.key == key)
    d1 = next(c for c in high.contrast if c.key == key)
    # The default run's Δ is unchanged; only the overridden run moves.
    assert d1.default_delta == d0.default_delta
    assert d1.overridden_delta != d1.default_delta
    assert abs(d1.shift) > 0


def test_out_of_range_override_is_clamped_and_flagged() -> None:
    """SPEC §34 honesty: out-of-range requests are clamped + flagged, not hidden."""
    res = rerun_with_assumptions(_policy(), {"money_to_minutes": 999.0})
    ov = next(o for o in res.overrides if o.name == "money_to_minutes")
    assert ov.requested == 999.0
    assert ov.applied == ov.high
    assert ov.clamped is True
    assert ov.in_range is False
    assert ov.note


def test_unknown_assumption_rejected() -> None:
    try:
        rerun_with_assumptions(_policy(), {"not_a_real_knob": 1.0})
    except UnknownAssumption as exc:
        assert "not_a_real_knob" in str(exc)
        assert exc.available
    else:  # pragma: no cover
        raise AssertionError("expected UnknownAssumption")


def test_unknown_assumption_returns_404_over_http() -> None:
    res = client.post("/assumptions/rerun", json=_rerun_body({"nope": 1.0}))
    assert res.status_code == 404
    assert "overridable_assumptions" in res.json()["detail"]


def test_rerun_is_deterministic() -> None:
    """Same body ⇒ byte-identical JSON (SPEC §34 reproducibility)."""
    body = _rerun_body({"money_to_minutes": 10.0, "car_cost_per_km": 0.30})
    a = client.post("/assumptions/rerun", json=body)
    b = client.post("/assumptions/rerun", json=body)
    assert a.status_code == b.status_code == 200
    assert a.json() == b.json()


def test_delta_band_still_widens_with_horizon() -> None:
    """Overriding assumptions must not break the §34 widening-uncertainty invariant."""
    res = rerun_with_assumptions(_policy(), {"money_to_minutes": 11.0})
    series = next(
        s for s in res.delta.series if s.key == "traffic.daily_vehicle_km"
    )
    widths = [p.high - p.low for p in series.points]
    assert all(b >= a - 1e-9 for a, b in zip(widths, widths[1:])), "band must not narrow"
    assert widths[-1] > widths[1], "far-horizon band should be strictly wider than near term"
    for p in series.points:
        assert p.low <= p.delta <= p.high


def test_horizon_defaults_to_year_two() -> None:
    res = rerun_with_assumptions(_policy(), {})
    assert res.horizon.t_months == 24.0
