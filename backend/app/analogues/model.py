"""Historical Analogue / Causal Layer (SPEC §7.1).

Estimate the flagship cordon-traffic effect of an input policy from *comparable
real-world schemes* instead of from the synthetic-city agent model:

1. For each historical case, compute a **difference-in-differences** effect —
   the treated cordon change minus the background/control trend — which strips
   out the city-wide trend the scheme did not cause.
2. Score each case's **transferability** to the input policy from auditable
   factors (intervention family, charge strength, revenue recycling, city
   context).
3. Pool the applicable cases by ``identification_strength × transferability`` into
   a central estimate + a confidence interval that widens when the evidence is
   weak or the analogues disagree.
4. Optionally cross-check against the agent-based model (SPEC §8 honesty): if the
   ABM predicts a far larger effect than any real scheme achieved, say so.

Every historical outcome is Observed (a real, published effect, flagged
illustrative); the transfer to this policy is Estimated. No LLM touches any
number (SPEC §7.1/§34).
"""

from __future__ import annotations

from ..baseline.model import compute_baseline
from ..baseline.schema import MetricTag
from ..baseline.timeseries import build_timeseries
from ..policy.dsl import InterventionType, PolicyDSL
from ..simulation.compare import build_delta
from ..simulation.shocks import apply_shocks
from ..simulation.timeline import build_world_b_timeline
from .cases import (
    CASES,
    CHARGE_HIGH,
    CHARGE_LOW,
    CHARGE_MODERATE,
    CHARGE_NONE,
    CHARGE_STRENGTH_LABEL,
    charge_strength,
)
from .schema import (
    AnalogueEstimate,
    CaseEstimate,
    HistoricalCase,
    StructuralComparison,
)

_FLAGSHIP_KEY = "traffic.vehicle_trips_into_cbd"

# Intervention families that levy a per-entry charge (share a pricing mechanism).
_PRICING_FAMILIES = {"road_pricing", "parking_levy", "low_emission_zone"}

# Documented transferability weights (auditable, sum to 1.0).
_TRANSFER_WEIGHTS = {"family": 0.35, "charge": 0.25, "reinvest": 0.15, "context": 0.25}


def _clip_reduction(pct: float) -> float:
    """Clamp a traffic reduction to the physically valid range [-100%, 0%]."""
    return max(-100.0, min(0.0, pct))


def _input_family(policy: PolicyDSL) -> str:
    return policy.intervention.type.value


def _input_reinvests_transit(policy: PolicyDSL) -> bool:
    return policy.revenue_allocation.public_transport >= 0.5


def _input_charge_bucket(policy: PolicyDSL) -> int:
    """Coarse 0–3 charge-strength bucket for the input policy (Estimated)."""
    if _input_family(policy) not in _PRICING_FAMILIES:
        return CHARGE_NONE
    amount = policy.intervention.amount or 0.0
    if amount <= 0:
        return CHARGE_NONE
    if amount <= 4:
        return CHARGE_LOW
    if amount <= 9:
        return CHARGE_MODERATE
    return CHARGE_HIGH


def _family_match(input_family: str, case_family: str) -> tuple[bool, float]:
    """Return (applicable, family_match_factor) for a case vs the input policy."""
    if input_family == case_family:
        return True, 1.0
    if input_family in _PRICING_FAMILIES and case_family in _PRICING_FAMILIES:
        # Both price/restrict cordon access via a similar mechanism.
        return True, 0.6
    return False, 0.0


def _transferability(
    policy: PolicyDSL, case: HistoricalCase
) -> tuple[bool, float, dict]:
    """Compute (applicable, transferability_score, factor breakdown) for one case."""
    input_family = _input_family(policy)
    applicable, family_factor = _family_match(input_family, case.intervention_family)
    if not applicable:
        return False, 0.0, {"family": round(family_factor, 3), "applicable": False}

    input_bucket = _input_charge_bucket(policy)
    case_bucket = charge_strength(case.id)
    charge_factor = 1.0 - abs(input_bucket - case_bucket) / 3.0

    reinvest_factor = 1.0 if _input_reinvests_transit(policy) == case.reinvested_in_transit else 0.6
    context_factor = case.context_similarity

    score = (
        _TRANSFER_WEIGHTS["family"] * family_factor
        + _TRANSFER_WEIGHTS["charge"] * charge_factor
        + _TRANSFER_WEIGHTS["reinvest"] * reinvest_factor
        + _TRANSFER_WEIGHTS["context"] * context_factor
    )
    factors = {
        "family": round(family_factor, 3),
        "charge_strength": round(charge_factor, 3),
        "revenue_recycling": round(reinvest_factor, 3),
        "city_context": round(context_factor, 3),
    }
    return True, round(max(0.0, min(1.0, score)), 3), factors


def _did(case: HistoricalCase) -> float:
    """Difference-in-differences effect = treated change − control (background) change."""
    return _clip_reduction(case.treated_change_pct - case.control_change_pct)


def _case_estimate(policy: PolicyDSL, case: HistoricalCase) -> CaseEstimate:
    applicable, transfer, factors = _transferability(policy, case)
    did = _did(case)
    quality = round(case.identification_strength * transfer, 3) if applicable else 0.0
    note = ""
    if not applicable:
        note = (
            f"{case.intervention_family.replace('_', ' ')} scheme — different mechanism "
            f"to this {_input_family(policy).replace('_', ' ')} policy; shown for context, not pooled."
        )
    return CaseEstimate(
        case_id=case.id,
        name=case.name,
        year=case.year,
        applicable=applicable,
        did_effect_pct=round(did, 2),
        identification_strength=case.identification_strength,
        transferability_score=transfer,
        analogue_quality=quality,
        pool_weight=0.0,  # filled in after normalisation
        transfer_factors=factors,
        note=note,
        tag=MetricTag.observed,
    )


def _quality_label(avg_quality: float, n_applicable: int) -> str:
    if n_applicable == 0:
        return "weak"
    if avg_quality >= 0.5:
        return "strong"
    if avg_quality >= 0.3:
        return "moderate"
    return "weak"


def _structural_flagship_pct(policy: PolicyDSL, horizon_months: float) -> tuple[float, str]:
    """The agent-based World-B model's own flagship cordon Δ% at the horizon (Simulated)."""
    params, trend = apply_shocks(None)
    base = compute_baseline(params)
    base_ts = build_timeseries(base, trend)
    b_ts = build_world_b_timeline(policy, baseline=base, params=params, trend=trend)
    delta = build_delta(base_ts, b_ts)
    cp_idx = max(
        (i for i, cp in enumerate(delta.checkpoints) if cp.t_months <= horizon_months),
        default=len(delta.checkpoints) - 1,
    )
    label = delta.checkpoints[cp_idx].label
    for s in delta.series:
        if s.key == _FLAGSHIP_KEY and s.points:
            return round(s.points[cp_idx].delta_pct or 0.0, 2), label
    return 0.0, label


def _agreement(structural: float, analogue: float) -> tuple[str, str]:
    gap = abs(structural - analogue)
    if gap < 10.0:
        return "consistent", (
            "The agent-based model and the real-world analogues broadly agree on "
            "the magnitude — higher confidence in this range."
        )
    if gap < 25.0:
        return "moderate gap", (
            "The agent-based model predicts a somewhat larger effect than the "
            "real-world analogues; treat the upper end as optimistic."
        )
    return "large gap", (
        "The agent-based model predicts a far larger cordon reduction than any "
        "comparable real scheme achieved. Real flat cordons rarely exceed ~30%. "
        "Lean on the analogue range as an empirical sanity floor and treat the "
        "model's magnitude as genuinely uncertain (SPEC §8)."
    )


def run_analogues(
    policy: PolicyDSL,
    horizon_months: float = 24.0,
    include_structural_comparison: bool = True,
) -> AnalogueEstimate:
    """Build the Historical Analogue / Causal Layer estimate for a policy (SPEC §7.1)."""
    input_family = _input_family(policy)
    cases = [_case_estimate(policy, c) for c in CASES]
    applicable = [c for c in cases if c.applicable]

    # Pool applicable cases by identification-weighted transferability.
    weight_sum = sum(c.analogue_quality for c in applicable)
    if applicable and weight_sum > 0:
        for c in applicable:
            c.pool_weight = round(c.analogue_quality / weight_sum, 3)
        central = sum(c.did_effect_pct * (c.analogue_quality / weight_sum) for c in applicable)
        effects = [c.did_effect_pct for c in applicable]
        lo_edge, hi_edge = min(effects), max(effects)
        avg_quality = weight_sum / len(applicable)
        # Widen the band when the pooled evidence is weak (low avg quality).
        span = hi_edge - lo_edge
        extra = span * (1.0 - avg_quality) * 0.5 + 3.0  # +3pp floor for transfer risk
        ci_low = _clip_reduction(lo_edge - extra)
        ci_high = _clip_reduction(hi_edge + extra)
        transferability = round(
            sum(c.transferability_score * (c.analogue_quality / weight_sum) for c in applicable), 3
        )
        quality_label = _quality_label(avg_quality, len(applicable))
        estimated = round(central, 2)
    else:
        # No comparable scheme (e.g. a transit-only or 'other' policy).
        avg_quality = 0.0
        estimated, ci_low, ci_high, transferability = 0.0, 0.0, 0.0, 0.0
        quality_label = "weak"

    diagnostics = _build_diagnostics(policy, applicable, cases)

    structural_comparison = None
    if include_structural_comparison:
        structural_pct, horizon_label = _structural_flagship_pct(policy, horizon_months)
        agreement, interp = _agreement(structural_pct, estimated)
        structural_comparison = StructuralComparison(
            structural_effect_pct=structural_pct,
            analogue_effect_pct=estimated,
            gap_pct_points=round(structural_pct - estimated, 2),
            agreement=agreement,
            interpretation=interp,
        )
    else:
        _, horizon_label = _structural_flagship_pct(policy, horizon_months)

    return AnalogueEstimate(
        policy_id=policy.id,
        intervention_family=input_family,
        horizon_label=horizon_label,
        estimated_effect_pct=estimated,
        ci_low_pct=round(ci_low, 2),
        ci_high_pct=round(ci_high, 2),
        analogue_quality=quality_label,
        transferability_score=transferability,
        cases=cases,
        identification_diagnostics=diagnostics,
        structural_comparison=structural_comparison,
        not_modelled=[
            "Illustrative, approximate published headline effects — not a live "
            "causal-inference pipeline over this city's microdata.",
            "A single flat cordon-traffic headline; no per-corridor, per-mode or "
            "distributional transfer (those live in the spatial/microsim layers).",
            "Transfer assumes a broadly similar behavioural response; genuine "
            "synthetic-control / IV estimation would need the treated city's panel data.",
            "Charge comparison is a coarse none/low/moderate/high bucket, not a "
            "purchasing-power-adjusted amount (Estimated).",
        ],
    )


def _build_diagnostics(
    policy: PolicyDSL, applicable: list[CaseEstimate], cases: list[CaseEstimate]
) -> list[str]:
    """Assemble SPEC §7.1 parallel-trend / identification diagnostics."""
    from .cases import CASES_BY_ID

    diagnostics: list[str] = []
    if not applicable:
        diagnostics.append(
            f"No comparable real-world scheme for a '{_input_family(policy)}' policy in "
            "the analogue base — the causal layer cannot transfer an effect here; rely "
            "on the structural model instead."
        )
        return diagnostics

    # Surface the parallel-trend caveat of the top contributing cases.
    top = sorted(applicable, key=lambda c: c.analogue_quality, reverse=True)[:3]
    for c in top:
        case = CASES_BY_ID[c.case_id]
        diagnostics.append(
            f"{case.name} ({case.design}): DiD isolates {c.did_effect_pct:.0f}% "
            f"(treated {case.treated_change_pct:.0f}% − control {case.control_change_pct:.0f}%). "
            f"{case.parallel_trend_note}"
        )
    diagnostics.append(
        "DiD strips the background trend from each scheme's raw before/after, but "
        "true parallel-trends and confounder control would require the treated "
        "city's panel data — these are transfer estimates, not on-site evaluations."
    )
    return diagnostics
