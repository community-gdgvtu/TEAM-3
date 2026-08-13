"""Integrity checks for the synthetic commuter population (``data/city/population.json``).

Structural / referential assertions (SPEC §6) that stay stable if the generator
is re-tuned — plus the ROADMAP M2 floor of >= 5000 micro-agents and the SPEC §34
provenance guardrail.
"""

from __future__ import annotations

from app import dataset

_VALID_BANDS = {"low", "lower-middle", "middle", "upper-middle", "upper"}


def test_population_is_synthetic_and_above_floor() -> None:
    pop = dataset.load_population()
    assert pop["provenance"] == "Synthetic"
    assert pop["generated_by"].endswith("generate_population.py")
    agents = pop["agents"]
    assert len(agents) >= 5000, "ROADMAP M2 requires >= 5k micro-agents"
    assert pop["summary"]["agents"] == len(agents)


def test_agent_ids_unique() -> None:
    agents = dataset.population_agents()
    ids = [a["agent_id"] for a in agents]
    assert len(ids) == len(set(ids))


def test_home_and_work_zones_reference_real_zones() -> None:
    zones = set(dataset.zone_index())
    for a in dataset.population_agents():
        assert a["home_zone"] in zones
        assert a["work_zone"] in zones


def test_commutes_into_cbd_flag_matches_work_zone() -> None:
    cbd = dataset.cbd_zone_ids()
    for a in dataset.population_agents():
        assert a["commutes_into_cbd"] == (a["work_zone"] in cbd)


def test_required_attributes_present_and_in_range() -> None:
    required = {
        "agent_id", "age", "household_size", "income", "income_band",
        "occupation", "home_zone", "work_zone", "car_access",
        "public_transit_access", "baseline_commute_minutes", "risk_aversion",
        "price_sensitivity", "policy_salience",
    }
    for a in dataset.population_agents():
        assert required <= a.keys()
        assert a["income_band"] in _VALID_BANDS
        assert a["income"] > 0
        assert 18 <= a["age"] <= 70
        assert a["household_size"] >= 1
        assert a["baseline_commute_minutes"] > 0
        for field in ("risk_aversion", "price_sensitivity", "policy_salience"):
            assert 0.0 <= a[field] <= 1.0, field
        assert isinstance(a["car_access"], bool)
        assert isinstance(a["public_transit_access"], bool)
        # everyone can reach work by some mode
        assert a["car_access"] or a["public_transit_access"]


def test_summary_income_bands_cover_population() -> None:
    pop = dataset.load_population()
    band_counts = pop["summary"]["income_band_counts"]
    assert sum(band_counts.values()) == len(pop["agents"])
    assert set(band_counts) <= _VALID_BANDS
