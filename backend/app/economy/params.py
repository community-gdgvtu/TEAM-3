"""Transparent economic-translation assumptions for the spillover layer (SPEC §7.4).

These are the elasticities / input-output ratios that turn the *physical*
simulation outputs (mode shifts, charge revenue, travel-cost changes — all
Simulated) into *monetary* local-economy channels. They are deliberately few,
documented and auditable: no LLM produces or tunes them (SPEC §34), and because
they are approximate behavioural coefficients layered on the Simulated core,
every number they produce is tagged **Estimated** (SPEC §8), never Simulated.

An MVP §7.4 layer, honest about its own limits: partial-equilibrium only — no
CGE, no heterogeneous-agent macro, no agglomeration or land-value effects, and
freight/shopper demand is not agent-modelled (surfaced as explicit assumptions).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class EconParams:
    """Input-output / elasticity assumptions for the economic spillover layer."""

    # --- Household consumption channel -------------------------------------
    #: Marginal propensity to consume locally out of income the charge removes
    #: from household discretionary budgets. A charge is a transfer, not a pure
    #: loss, so only the locally-spent fraction leaves the local economy before
    #: recycling. Range reflects how much charged spend was local vs. saved/import.
    local_consumption_mpc: float = 0.55
    local_consumption_mpc_range: tuple[float, float] = (0.40, 0.70)

    # --- Revenue recycling / fiscal multiplier -----------------------------
    #: Local expenditure multiplier on recycled public revenue (transit ops +
    #: capital are labour-intensive and largely locally spent). >1 because each
    #: currency unit re-spent circulates. Conservative local-multiplier range.
    fiscal_multiplier: float = 1.40
    fiscal_multiplier_range: tuple[float, float] = (1.10, 1.70)
    #: Share of recycled revenue that is actually re-spent inside the local
    #: economy (rest leaks to imports / non-local suppliers).
    revenue_local_share: float = 0.80

    # --- Value of commuter time (labour / welfare channel) -----------------
    #: Currency value of one commuter-minute. Deliberately the *inverse* of the
    #: mode-choice model's ``money_to_minutes`` so the economic layer prices time
    #: consistently with the generalized-cost model that produced the mode
    #: switches. Set at runtime from BaselineParams; this is only a fallback.
    fallback_value_of_time_per_min: float = 0.125
    #: Multiplicative band on the value of time (VoT is inherently uncertain).
    value_of_time_range_mult: tuple[float, float] = (0.6, 1.5)

    # --- CBD retail / footfall channel -------------------------------------
    #: Retail turnover uplift from pedestrianising a central district (amenity
    #: effect — calmer, more walkable streets raise dwell time and spend). An
    #: Estimated effect from the transport-economics literature, NOT derived from
    #: agent behaviour (no shopper agents), applied only to pedestrianisation.
    pedestrianisation_retail_uplift: float = 0.06
    pedestrianisation_retail_uplift_range: tuple[float, float] = (-0.02, 0.15)
    #: Annual retail/hospitality turnover exposed per CBD-bound commuter — a
    #: transparent scaling from commuter volume to central discretionary spend.
    cbd_retail_spend_per_commuter_year: float = 900.0
    #: Fraction of deterred CBD car trips that represent a trip *not made at all*
    #: (destination substitution) rather than a mode switch to still-arriving
    #: transit/walk. Commuting is conserved in the sim, so this is the small
    #: discretionary-trip loss a charge causes; Estimated.
    cbd_trip_avoidance_fraction: float = 0.10
    cbd_trip_avoidance_fraction_range: tuple[float, float] = (0.03, 0.20)

    # --- Business logistics / freight channel ------------------------------
    #: Freight/delivery share of vehicle entries into the cordon. Freight is not
    #: in the synthetic population, so this is a documented ratio, not a modelled
    #: count — the channel it feeds is Estimated with low confidence.
    freight_entry_share: float = 0.12
    freight_entry_share_range: tuple[float, float] = (0.06, 0.20)
    #: Share of the freight charge cost passed through to CBD business/consumers.
    freight_cost_pass_through: float = 0.70

    def value_of_time_per_min(self, money_to_minutes: float) -> float:
        """Consistent VoT: inverse of the GC model's money↔time conversion."""
        return 1.0 / money_to_minutes if money_to_minutes > 0 else (
            self.fallback_value_of_time_per_min
        )

    def as_dict(self) -> dict:
        return asdict(self)


#: The default economic-translation assumption set.
DEFAULT_ECON_PARAMS = EconParams()
