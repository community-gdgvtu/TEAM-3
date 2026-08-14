"""Transparent stocks-and-flows coefficients for the System Dynamics layer.

These describe *how* the recursive feedback loop of SPEC §19 evolves over time
(rates, lags, thresholds) — they are **input assumptions**, auditable and fixed,
never LLM outputs. The *magnitudes* the loop pushes toward (how much a given
charge shifts demand, how much revenue it raises, how popular it is) all come
from the deterministic agent-based model, not from here.

Provenance (SPEC §34): the structural anchors are Simulated (ABM); these temporal
coefficients are documented Estimated inputs. The integrated trajectory is a
deterministic simulation output → Simulated, LLM-free.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class SystemDynamicsParams:
    """Stocks-and-flows dynamics + endogenous political-response assumptions."""

    # --- integration ------------------------------------------------------
    #: Total horizon simulated (months). 120 = the 10-year Time Machine end.
    horizon_months: int = 120
    #: Fixed integration step (months). Monthly Euler steps.
    step_months: int = 1

    # --- behavioural substitution (demand flow) ---------------------------
    #: Time-constant of the demand stock relaxing toward the charge's structural
    #: pull (months). Commuters re-choose mode quickly once a charge lands/changes.
    behaviour_tau_months: float = 2.0
    #: Time-constant of the collected-revenue stock tracking the behavioural
    #: response (months) — revenue realises as fast as the paying behaviour settles.
    revenue_tau_months: float = 2.0

    # --- transit capacity (supply stock funded by revenue) ----------------
    #: Sizing headroom of the pre-policy peak transit network over current peak
    #: CBD-bound demand (network built ~15% above today's peak).
    capacity_headroom: float = 1.15
    #: Years of *nominal-charge* reinvestment the capacity programme is scoped to
    #: cost. The plan is sized at announcement; if the charge is later cut the
    #: programme cost stays fixed, so completion stalls (this is the §19 loop).
    capacity_programme_years: float = 4.0
    #: Maximum peak-capacity uplift a fully-funded programme delivers (fraction of
    #: baseline capacity). Estimated network-engineering ceiling.
    max_capacity_uplift: float = 0.35
    #: Lag before any funded capacity is delivered (months) — planning + build.
    capacity_lag_months: float = 6.0
    #: Delivery time-constant of capacity toward its funded target (months).
    capacity_build_tau_months: float = 18.0

    # --- opinion dynamics + crowding feedback -----------------------------
    #: Stickiness of the support stock relaxing toward its target (months).
    support_tau_months: float = 4.0
    #: Support erosion per unit of sustained over-capacity crowding
    #: (support points lost at crowding = 2.0×). Estimated.
    crowding_penalty: float = 0.6
    #: Crowding ratio (demand/capacity) above which riders feel over-capacity.
    crowding_onset: float = 1.0

    # --- endogenous political response (SPEC §19) -------------------------
    #: Net-support level below which political pressure to amend builds.
    political_threshold: float = -0.15
    #: Consecutive months below the threshold before an amendment is forced.
    patience_months: int = 6
    #: Fraction the charge is cut to when an amendment fires (0.6 = −40%).
    charge_cut_factor: float = 0.6
    #: Maximum number of endogenous amendments over the horizon.
    max_amendments: int = 2
    #: Charge floor — amendments never cut below this (currency).
    charge_floor: float = 1.0

    # --- confidence band (SPEC §9/§24) ------------------------------------
    confidence_base: float = 0.85
    confidence_decay_per_year: float = 0.055
    confidence_floor: float = 0.3

    def as_dict(self) -> dict:
        return asdict(self)


DEFAULT_SD_PARAMS = SystemDynamicsParams()
