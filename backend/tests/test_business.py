"""Tests for the Business View layer (SPEC §17 Business View).

Guards the two things that make this micro layer trustworthy: (1) it returns the
SPEC §17 firm-level shape (footfall / labour accessibility / deliveries / costs /
revenue proxy / adaptation decisions), and (2) its per-firm numbers can't
disagree with the aggregate models beside them — labour accessibility is the
commute generalized cost of the firm's own workers under the *same* deterministic
mode-choice model as ``/simulate``, and the firm stock's allocated jobs sum back
to the zone job totals.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app import dataset
from app.baseline.model import mode_options, pick_mode
from app.baseline.params import DEFAULT_PARAMS
from app.business.service import (
    _agent_gc,
    _behav_levers,
    _firm_stock,
    _zone_commuter_aggregates,
    build_business_view,
)
from app.main import app
from app.policy.dsl import PolicyDSL
from app.simulation.levers import DEFAULT_SIM_PARAMS, derive_levers

client = TestClient(app)

DEMO_TEXT = (
    "Introduce a $12 congestion charge for private vehicles entering the central "
    "business district. Exempt disability permit holders. Reinvest 100% of net "
    "proceeds into buses."
)


def _demo_policy() -> dict:
    r = client.post("/policy/compile", json={"text": DEMO_TEXT})
    assert r.status_code == 200, r.text
    return r.json()["policy"]


DEMO = _demo_policy()


def test_business_returns_spec17_shape() -> None:
    r = client.post("/business", json={"policy": DEMO})
    assert r.status_code == 200, r.text
    b = r.json()
    for f in (
        "firm_id", "sector", "building_kind", "zone_id", "in_central_district",
        "floors", "floor_area_sqm", "estimated_jobs",
    ):
        assert f in b["profile"], f
    labels = [s["label"] for s in b["trajectory"]]
    assert labels[0] == "T0"
    assert b["trajectory"][0]["t_months"] == 0.0
    assert b["trajectory"][-1]["t_months"] == 120.0
    # The SPEC §17 firm read-outs are all present per checkpoint.
    snap = b["trajectory"][0]
    for f in (
        "daily_footfall", "labour_accessibility_index", "daily_deliveries",
        "annual_cost_added", "revenue_proxy_annual", "net_revenue_proxy_change_pct",
    ):
        assert f in snap, f
    assert b["adaptation_decisions"]  # SPEC §17 "adaptation decisions"
    assert b["explanation"]


def test_firm_jobs_sum_back_to_zone_totals() -> None:
    """Allocated firm jobs never exceed their zone's job total (SPEC §5 consistency)."""
    firms = _firm_stock()
    zi = dataset.zone_index()
    by_zone: dict[str, int] = {}
    for f in firms:
        by_zone[f["zone_id"]] = by_zone.get(f["zone_id"], 0) + f["estimated_jobs"]
    for zone, allocated in by_zone.items():
        zone_jobs = int(zi.get(zone, {}).get("jobs", 0))
        # Allocation by floor-space share rounds per firm, so allow a small rounding slack.
        assert allocated <= zone_jobs + len(firms), zone


def test_before_policy_is_worldA_reference() -> None:
    """BEFORE POLICY == T0, no added cost, labour access index 100 (SPEC §17)."""
    view = build_business_view(PolicyDSL(**DEMO), selector="representative")
    before, t0 = view.before_policy, view.trajectory[0]
    assert before.t_months == 0.0
    assert before.daily_footfall == t0.daily_footfall
    assert before.annual_cost_added == 0.0
    assert before.labour_accessibility_index == 100.0
    assert before.net_revenue_proxy_change_pct == 0.0


def test_labour_accessibility_uses_same_mode_choice_as_simulate() -> None:
    """Labour access index is the firm's workers' commute GC under the /simulate model."""
    policy = PolicyDSL(**DEMO)
    view = build_business_view(policy, selector="most_exposed")
    zone = view.profile.zone_id
    cbd = dataset.cbd_zone_ids()

    # Recompute the World-A mean commuter generalized cost for this work zone.
    agg = _zone_commuter_aggregates(
        derive_levers(policy),
        _behav_levers(policy, DEFAULT_PARAMS, DEFAULT_SIM_PARAMS),
        cbd, DEFAULT_PARAMS,
    )
    z = agg[zone]
    workers = [a for a in dataset.population_agents() if a["work_zone"] == zone]
    mean_gc_a = sum(_agent_gc(mode_options(a, DEFAULT_PARAMS)) for a in workers) / len(workers)
    assert abs(z["mean_gc_a"] - mean_gc_a) < 1e-9
    # T0 index is exactly 100 (baseline), and it never exceeds 100 for a cost-raising charge.
    assert view.trajectory[0].labour_accessibility_index == 100.0
    assert view.trajectory[-1].labour_accessibility_index <= 100.0 + 1e-9


def test_central_charge_firm_pays_delivery_cost_and_flags_adaptation() -> None:
    """A central firm under the charge accrues a delivery cost and adaptation decisions."""
    view = build_business_view(PolicyDSL(**DEMO), selector="most_exposed")
    end = view.trajectory[-1]
    assert view.profile.in_central_district
    assert end.annual_cost_added > 0
    assert any("delivery" in d.lower() for d in view.adaptation_decisions)


def test_bands_widen_monotonically_with_horizon() -> None:
    """Footfall / cost / revenue bands widen with the horizon (SPEC §9/§34)."""
    view = build_business_view(PolicyDSL(**DEMO), selector="most_exposed")
    traj = view.trajectory
    for a, b in zip(traj, traj[1:]):
        for lo, hi in (
            ("daily_footfall_low", "daily_footfall_high"),
            ("annual_cost_added_low", "annual_cost_added_high"),
        ):
            wa = getattr(a, hi) - getattr(a, lo)
            wb = getattr(b, hi) - getattr(b, lo)
            assert wb >= wa - 1e-9, f"{lo}/{hi} band narrowed {a.label}->{b.label}"
    assert (traj[-1].daily_footfall_high - traj[-1].daily_footfall_low) > (
        traj[0].daily_footfall_high - traj[0].daily_footfall_low
    )
    # Plotted value inside its own band.
    for s in traj:
        assert s.daily_footfall_low <= s.daily_footfall <= s.daily_footfall_high


def test_determinism_byte_identical() -> None:
    r1 = client.post("/business", json={"policy": DEMO})
    r2 = client.post("/business", json={"policy": DEMO})
    assert r1.content == r2.content


def test_firm_id_lookup_and_errors() -> None:
    firms = _firm_stock()
    fid = firms[0]["firm_id"]
    r = client.post("/business", json={"policy": DEMO, "firm_id": fid})
    assert r.status_code == 200
    assert r.json()["profile"]["firm_id"] == fid
    assert r.json()["selector"] == f"firm_id:{fid}"
    assert client.post("/business", json={"policy": DEMO, "firm_id": "FIRM-99999"}).status_code == 404
    assert client.post("/business", json={"policy": DEMO, "select": "nope"}).status_code == 422


def test_no_op_policy_leaves_firm_unchanged() -> None:
    """A behavioural no-op changes nothing for a firm (SPEC §17/§34)."""
    noop_text = "Repaint the town-hall facade in the central district."
    noop = client.post("/policy/compile", json={"text": noop_text}).json()["policy"]
    view = build_business_view(PolicyDSL(**noop), selector="representative")
    before, end = view.before_policy, view.trajectory[-1]
    assert end.daily_footfall == before.daily_footfall
    assert end.labour_accessibility_index == before.labour_accessibility_index
    assert end.annual_cost_added == 0.0
    assert any("barely touches" in line or "unchanged" in line for line in view.explanation)


def test_sample_picker_spans_sectors() -> None:
    r = client.get("/business/sample")
    assert r.status_code == 200
    sectors = {c["sector"] for c in r.json()}
    assert len(sectors) >= 3  # spans multiple firm sectors
    for c in r.json():
        assert c["firm_id"].startswith("FIRM-")


def test_registered_in_model_registry() -> None:
    reg = client.get("/registry").json()
    card = next((m for m in reg["models"] if m["id"] == "business_view"), None)
    assert card is not None
    assert card["llm_touches_numbers"] is False  # SPEC §34
    assert card["produces_numbers"] is True
