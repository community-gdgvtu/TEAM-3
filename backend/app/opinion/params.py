"""Transparent assumptions for the cohort opinion model (SPEC §13).

Every constant here is an **input assumption** feeding the deterministic opinion
model in :mod:`app.opinion.model` — not an observed poll and not an LLM output.
They are surfaced for the Evidence Drawer so a human can correct them. The model
itself (material impact) is driven by the agent-based mode-choice output; these
parameters only weight and frame that structural signal.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass(frozen=True)
class OpinionParams:
    """Weights, priors and spreads for the cohort opinion model."""

    # --- Support-score weights (sum ~1.0) ----------------------------------
    w_material: float = 0.55  # how the policy changes this agent's own travel cost
    w_fairness: float = 0.30  # perceived fairness (regressivity, exemptions, reinvestment)
    w_prior: float = 0.15  # ideological prior

    # --- Material impact normalisation -------------------------------------
    #: Generalized-cost change (minutes-equivalent, one-way) that maps to a full
    #: ±1 material signal. Larger swings are clamped.
    material_scale_min: float = 18.0

    # --- Fairness components ------------------------------------------------
    fairness_regressive: float = 0.55  # low-income agent pays an unexempted flat charge
    fairness_exemption: float = 0.35  # agent benefits from an exemption they'd otherwise pay
    fairness_reinvest: float = 0.40  # goodwill for transit users when revenue funds transit
    fairness_reinvest_general: float = 0.10  # mild general goodwill from reinvestment
    fairness_coercion: float = 0.25  # forced off car by a ban

    # --- Ideological prior by income band (small, transparent lean) --------
    prior_by_band: dict = field(
        default_factory=lambda: {
            "low": 0.10,
            "lower-middle": 0.05,
            "middle": 0.0,
            "upper-middle": -0.05,
            "upper": -0.10,
        }
    )

    # --- Opinion distribution shape ----------------------------------------
    #: Spread of an agent's opinion around its latent support score.
    opinion_sigma: float = 0.42
    #: Base "uncertain" mass, scaled down by an agent's policy salience.
    uncertain_base: float = 0.28
    uncertain_floor: float = 0.03
    uncertain_cap: float = 0.35

    def prior_for(self, band: str) -> float:
        return float(self.prior_by_band.get(band, 0.0))

    def as_dict(self) -> dict:
        return asdict(self)


DEFAULT_OPINION_PARAMS = OpinionParams()
