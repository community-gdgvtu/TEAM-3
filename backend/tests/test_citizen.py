"""Tests for the Citizen View layer (SPEC §17 Citizen View, §31 Agent State).

Guards the two things that make this layer trustworthy: (1) it returns the SPEC
§17/§31 shape for a single household, and (2) its per-household numbers can never
disagree with the aggregate models beside them — the World-A/World-B mode/cost
come from the same deterministic mode-choice model as ``/simulate`` and the
far-horizon support equals the same per-agent function ``/public`` aggregates.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.baseline.model import CAR, mode_options, pick_mode
from app.baseline.params import DEFAULT_PARAMS
from app.citizen.service import _leg, build_citizen_view
from app.main import app
from app.opinion.model import _agent_support
from app.opinion.params import DEFAULT_OPINION_PARAMS
from app.policy.dsl import PolicyDSL
from app.simulation.levers import derive_levers
from app.simulation.model import policy_mode_options
from app import dataset

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


def test_citizen_returns_spec17_shape() -> None:
    r = client.post("/citizen", json={"policy": DEMO})
    assert r.status_code == 200, r.text
    b = r.json()
    # Profile (SPEC §17 "click a household").
    for f in (
        "agent_id", "income_monthly", "income_annual", "income_band",
        "occupation", "home_zone", "work_zone", "commutes_into_cbd",
        "commute_distance_km", "car_access", "public_transit_access",
    ):
        assert f in b["profile"], f
    # A checkpoint per Time-Machine horizon, T0 first, 10y last.
    labels = [s["label"] for s in b["trajectory"]]
    assert labels[0] == "T0"
    assert b["trajectory"][0]["t_months"] == 0.0
    assert b["trajectory"][-1]["t_months"] == 120.0
    # §31 Agent State record per checkpoint, with the exact field set.
    assert len(b["agent_states"]) == len(b["trajectory"])
    st = b["agent_states"][0]
    for f in ("agent_id", "t", "location", "income", "commute_minutes",
              "monthly_transport_cost", "policy_support"):
        assert f in st, f
    assert st["location"] == b["profile"]["home_zone"]
    assert b["explanation"]  # a non-empty "why?" narrative


def test_before_policy_equals_t0_and_worldA() -> None:
    """BEFORE POLICY is the World-A reference and matches T0 (SPEC §17)."""
    view = build_citizen_view(PolicyDSL(**DEMO), selector="most_burdened")
    before = view.before_policy
    t0 = view.trajectory[0]
    assert before.t_months == 0.0
    assert before.commute_minutes_one_way == t0.commute_minutes_one_way
    assert before.monthly_transport_cost == t0.monthly_transport_cost
    assert before.charge_paid_monthly == 0.0  # no charge before the policy

    # The World-A commute equals this agent's baseline mode leg.
    agent = next(a for a in dataset.population_agents() if a["agent_id"] == view.profile.agent_id)
    base_mode = pick_mode(mode_options(agent, DEFAULT_PARAMS))
    minutes, _ = _leg(agent, base_mode, None, dataset.cbd_zone_ids(), DEFAULT_PARAMS)
    assert round(minutes, 1) == before.commute_minutes_one_way
    assert view.trajectory[0].mode == base_mode


def test_far_horizon_matches_worldB_mode_and_public_support() -> None:
    """The fully-adapted household state can't disagree with /simulate or /public."""
    policy = PolicyDSL(**DEMO)
    view = build_citizen_view(policy, selector="biggest_loser")
    agent = next(a for a in dataset.population_agents() if a["agent_id"] == view.profile.agent_id)
    cbd = dataset.cbd_zone_ids()
    levers = derive_levers(policy)

    # Far-horizon mode == the World-B (fully adapted) mode-choice for this agent.
    full_mode = pick_mode(policy_mode_options(agent, levers, cbd, DEFAULT_PARAMS))
    assert view.trajectory[-1].mode == full_mode

    # Far-horizon support == this agent's own /public opinion contribution.
    base_opts = mode_options(agent, DEFAULT_PARAMS)
    base_mode = pick_mode(base_opts)
    base_cost = base_opts[base_mode]
    pol_opts = policy_mode_options(agent, levers, cbd, DEFAULT_PARAMS)
    pol_mode = pick_mode(pol_opts)
    pol_cost = pol_opts[pol_mode]
    into_cbd = agent["commutes_into_cbd"]
    exempt = levers.is_exempt(agent, cbd)
    paid = pol_mode == CAR and into_cbd and levers.charge_per_one_way > 0 and not exempt
    would_pay = into_cbd and levers.charge_per_one_way > 0 and agent["car_access"] and not levers.car_banned_in_cbd
    exempt_benefit = would_pay and exempt and pol_mode == CAR
    forced = base_mode == CAR and into_cbd and levers.car_banned_in_cbd and pol_mode != CAR
    pt_share = float(policy.revenue_allocation.public_transport or 0.0)
    _, _, support = _agent_support(
        agent, base_cost, pol_cost, pol_mode, paid, exempt_benefit, forced,
        levers, pt_share, DEFAULT_OPINION_PARAMS,
    )
    assert view.trajectory[-1].policy_support == round(support, 3)


def test_bands_widen_monotonically_with_horizon() -> None:
    """The per-household commute/cost band must widen with the horizon (SPEC §9/§34)."""
    view = build_citizen_view(PolicyDSL(**DEMO), selector="biggest_winner")
    traj = view.trajectory
    for a, b in zip(traj, traj[1:]):
        wa = a.commute_minutes_high - a.commute_minutes_low
        wb = b.commute_minutes_high - b.commute_minutes_low
        assert wb >= wa - 1e-9, f"commute band narrowed {a.label}->{b.label}"
        ca = a.monthly_transport_cost_high - a.monthly_transport_cost_low
        cb = b.monthly_transport_cost_high - b.monthly_transport_cost_low
        assert cb >= ca - 1e-9, f"cost band narrowed {a.label}->{b.label}"
    # And the far band is strictly wider than T0 (a flat band would be dishonest).
    assert (traj[-1].commute_minutes_high - traj[-1].commute_minutes_low) > (
        traj[0].commute_minutes_high - traj[0].commute_minutes_low
    )
    # The plotted value always sits inside its own band.
    for s in traj:
        assert s.commute_minutes_low <= s.commute_minutes_one_way <= s.commute_minutes_high


def test_charge_payer_worse_off_and_opposed() -> None:
    """The most-burdened household pays the charge and opposes (SPEC §17 example)."""
    view = build_citizen_view(PolicyDSL(**DEMO), selector="most_burdened")
    end = view.trajectory[-1]
    assert end.charge_paid_monthly > 0
    assert end.monthly_transport_cost > view.before_policy.monthly_transport_cost
    assert end.policy_support < 0
    assert end.stance == "opposes"
    assert any("charge" in line.lower() for line in view.explanation)


def test_transit_winner_improves_over_time() -> None:
    """A reinvestment beneficiary's commute/cost improve as the uplift lands."""
    view = build_citizen_view(PolicyDSL(**DEMO), selector="biggest_winner")
    early = view.trajectory[1]  # 1 month — before the transit ramp
    late = view.trajectory[-1]  # 10 years — fully adapted
    assert late.commute_minutes_one_way <= early.commute_minutes_one_way + 1e-9
    assert late.monthly_transport_cost <= early.monthly_transport_cost + 1e-9
    assert late.policy_support >= view.trajectory[0].policy_support


def test_determinism_byte_identical() -> None:
    r1 = client.post("/citizen", json={"policy": DEMO})
    r2 = client.post("/citizen", json={"policy": DEMO})
    assert r1.content == r2.content


def test_agent_id_lookup_and_errors() -> None:
    # Explicit agent_id is honoured.
    r = client.post("/citizen", json={"policy": DEMO, "agent_id": "CIT-00001"})
    assert r.status_code == 200
    assert r.json()["profile"]["agent_id"] == "CIT-00001"
    assert r.json()["selector"] == "agent_id:CIT-00001"
    # Unknown agent → 404.
    assert client.post("/citizen", json={"policy": DEMO, "agent_id": "CIT-99999"}).status_code == 404
    # Unknown selector → 422.
    assert client.post("/citizen", json={"policy": DEMO, "select": "nope"}).status_code == 422


def test_no_op_policy_leaves_household_unchanged() -> None:
    """A behavioural no-op (no charge, no ban, no reinvestment) changes nothing."""
    noop_text = "Repaint the town-hall facade in the central district."
    noop = client.post("/policy/compile", json={"text": noop_text}).json()["policy"]
    view = build_citizen_view(PolicyDSL(**noop), selector="representative")
    before, end = view.before_policy, view.trajectory[-1]
    assert end.mode == before.mode
    assert end.commute_minutes_one_way == before.commute_minutes_one_way
    assert end.monthly_transport_cost == before.monthly_transport_cost
    assert end.charge_paid_monthly == 0.0
    assert any("does not change" in line for line in view.explanation)


def test_sample_picker_spans_income_bands() -> None:
    r = client.get("/citizen/sample")
    assert r.status_code == 200
    bands = {c["income_band"] for c in r.json()}
    # The synthetic city has five income bands; the picker should span them.
    assert {"low", "middle", "upper"} <= bands
    for c in r.json():
        assert c["agent_id"].startswith("CIT-")


def test_registered_in_model_registry() -> None:
    reg = client.get("/registry").json()
    ids = {m["id"] for m in reg["models"]}
    assert "citizen_view" in ids
    card = next(m for m in reg["models"] if m["id"] == "citizen_view")
    assert card["llm_touches_numbers"] is False  # SPEC §34
    assert card["produces_numbers"] is True
