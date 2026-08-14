"""Public-reaction (cohort opinion) package (ROADMAP M6, SPEC §13).

Deterministic model of heterogeneous public opinion: each synthetic micro-agent's
own modelled material impact plus perceived fairness and an ideological prior
yields a support distribution, aggregated by cohort and overall. No LLM touches
the numeric path (SPEC §34).
"""

from .model import compute_public_opinion
from .params import DEFAULT_OPINION_PARAMS, OpinionParams
from .schema import CohortOpinion, OpinionDistribution, PublicOpinion

__all__ = [
    "compute_public_opinion",
    "OpinionParams",
    "DEFAULT_OPINION_PARAMS",
    "CohortOpinion",
    "OpinionDistribution",
    "PublicOpinion",
]
