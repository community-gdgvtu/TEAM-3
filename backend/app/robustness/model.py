"""Decision-under-uncertainty engine (SPEC §20 + §21 + §22).

Given several **candidate** policies and a set of possible futures (the transparent
baseline plus the SPEC §20 named shocks), this scores every candidate in every
state, builds the regret matrix, and applies the classic decision criteria —
maximin, minimax-regret (Savage), Laplace, and the stress-test robustness rate —
so a minister can see whether the *headline* winner is also the *robust* choice.

It is a **pure composition** of the deterministic stress core: each payoff is the
exact same ``_run_delta`` the ``/stress-test`` and ``/simulate`` endpoints use, so
this layer can never disagree with them. No new numeric model, no randomness, no
LLM (SPEC §22/§34). Same inputs ⇒ same report.
"""

from __future__ import annotations

from ..policy.dsl import InterventionType, PolicyDSL
from ..stress.catalogue import ShockScenario, catalogue_keys, get_scenario
from ..stress.model import (  # reuse the exact deterministic stress primitives
    _HEADLINE,
    _ROBUST,
    _confidence,
    _delta_at,
    _horizon_label,
    _run_delta,
    _snap_horizon,
)
from .schema import (
    CandidateScore,
    DecisionPicks,
    RobustnessReport,
    StateResult,
)

# The objective metrics a decision can be framed around are exactly the stress
# headline metrics (key → intended direction of a *good* policy effect).
_OBJECTIVES: dict[str, str] = dict(_HEADLINE)
_DEFAULT_OBJECTIVE = "emissions.daily_co2_tonnes"


def objective_keys() -> list[str]:
    """Valid objective metric keys (for the router's 404 helper / UI)."""
    return list(_OBJECTIVES.keys())


def _candidate_label(policy: PolicyDSL) -> str:
    """A short human-readable description of a candidate policy."""
    iv = policy.intervention
    itype = iv.type.value if isinstance(iv.type, InterventionType) else str(iv.type)
    pretty = itype.replace("_", " ")
    if iv.amount is not None:
        pretty = f"{pretty} @ {iv.amount:g}"
    pt = policy.revenue_allocation.public_transport
    if pt > 0:
        pretty += f", {round(pt * 100)}% → transit"
    if "low-income" in policy.exemptions or "low_income" in policy.exemptions:
        pretty += ", low-income exempt"
    return pretty


def _objective_label(key: str) -> str:
    """Human label for the objective, pulled from a live delta series."""
    return _OBJECTIVE_LABELS.get(key, key)


# Stable labels for the headline objectives (match the delta series labels).
_OBJECTIVE_LABELS: dict[str, str] = {
    "traffic.vehicle_trips_into_cbd": "vehicle trips into the CBD",
    "emissions.daily_co2_tonnes": "daily CO₂ (tonnes)",
    "mode_share.car_pct": "car mode share (%)",
    "transit.daily_transit_trips": "daily transit trips",
}


def _resolve_states(keys: list[str] | None) -> list[ShockScenario | None]:
    """Return the ordered states of the world: baseline (None) then each shock.

    Raises ``KeyError`` (offending key) on an unknown shock, so the router can 404.
    """
    if not keys:
        shocks: list[ShockScenario] = list(_all_shocks())
    else:
        shocks = []
        for k in keys:
            sc = get_scenario(k)
            if sc is None:
                raise KeyError(k)
            shocks.append(sc)
    return [None, *shocks]  # baseline first


def _all_shocks() -> list[ShockScenario]:
    from ..stress.catalogue import SHOCK_CATALOGUE

    return list(SHOCK_CATALOGUE)


def _payoff(policy: PolicyDSL, shock: ShockScenario | None, objective: str, horizon: float):
    """Benefit (signed so higher = better) on the objective in one state."""
    intended = _OBJECTIVES[objective]
    sign_good = -1.0 if intended == "decrease" else 1.0
    delta = _run_delta(policy, shock.overrides if shock else None)
    series = next((s for s in delta.series if s.key == objective), None)
    if series is None:
        return 0.0, None
    d, d_pct = _delta_at(series, horizon)
    benefit = d * sign_good
    benefit_pct = None if d_pct is None else d_pct * sign_good
    return benefit, benefit_pct


def compare_robustness(
    candidates: list[PolicyDSL],
    scenario_keys: list[str] | None = None,
    objective: str | None = None,
    horizon_months: float | None = None,
) -> RobustnessReport:
    """Rank candidate policies by decision-under-uncertainty criteria.

    Raises ``KeyError`` on an unknown shock key or objective (router → 404),
    ``ValueError`` if fewer than two candidates are supplied.
    """
    if len(candidates) < 2:
        raise ValueError("need at least two candidate policies to compare")
    obj = objective or _DEFAULT_OBJECTIVE
    if obj not in _OBJECTIVES:
        raise KeyError(obj)

    horizon = _snap_horizon(horizon_months)
    states = _resolve_states(scenario_keys)  # baseline (None) first

    # payoff[candidate_idx][state_idx] and payoff_pct alongside.
    payoff: list[list[float]] = []
    payoff_pct: list[list[float | None]] = []
    for pol in candidates:
        row: list[float] = []
        row_pct: list[float | None] = []
        for st in states:
            b, b_pct = _payoff(pol, st, obj, horizon)
            row.append(b)
            row_pct.append(b_pct)
        payoff.append(row)
        payoff_pct.append(row_pct)

    # Per-state best payoff (for the regret matrix).
    best_in_state = [max(payoff[i][s] for i in range(len(candidates))) for s in range(len(states))]

    scores: list[CandidateScore] = []
    for i, pol in enumerate(candidates):
        state_results: list[StateResult] = []
        holds: list[str] = []
        fails: list[str] = []
        nominal = payoff[i][0]  # baseline is state 0
        n_shock = 0
        n_holds = 0
        for s, st in enumerate(states):
            key = "baseline" if st is None else st.key
            label = "Baseline (no shock)" if st is None else st.label
            category = "reference" if st is None else st.category
            fidelity = "modelled" if st is None else st.fidelity
            regret = round(best_in_state[s] - payoff[i][s], 4)
            # retained vs this candidate's OWN no-shock benefit (stress semantics).
            if st is None:
                retained_pct = None
            elif abs(nominal) <= 1e-9:
                retained_pct = None  # candidate had no benefit even at baseline
            else:
                retained = payoff[i][s] / nominal
                retained_pct = round(100.0 * retained, 1)
                n_shock += 1
                if retained >= _ROBUST:
                    n_holds += 1
                    holds.append(key)
                else:
                    fails.append(key)
            state_results.append(
                StateResult(
                    state_key=key,
                    state_label=label,
                    category=category,
                    payoff=round(payoff[i][s], 4),
                    payoff_pct=(None if payoff_pct[i][s] is None else round(payoff_pct[i][s], 2)),
                    regret=regret,
                    retained_pct=retained_pct,
                    confidence=_confidence(fidelity, horizon),
                )
            )
        row = payoff[i]
        robustness_score = round(n_holds / n_shock, 4) if n_shock else 0.0
        scores.append(
            CandidateScore(
                policy_id=pol.id,
                label=_candidate_label(pol),
                states=state_results,
                nominal_payoff=round(nominal, 4),
                worst_case_payoff=round(min(row), 4),
                best_case_payoff=round(max(row), 4),
                mean_payoff=round(sum(row) / len(row), 4),
                max_regret=round(max(sr.regret for sr in state_results), 4),
                robustness_score=robustness_score,
                holds_under=holds,
                fails_under=fails,
            )
        )

    picks = _decide(scores)
    headline = _headline(scores, picks, obj)

    return RobustnessReport(
        objective_key=obj,
        objective_label=_objective_label(obj),
        objective_direction=_OBJECTIVES[obj],
        horizon_months=horizon,
        horizon_label=_horizon_label(horizon),
        states=["baseline" if st is None else st.key for st in states],
        candidates=scores,
        picks=picks,
        headline=headline,
    )


def _decide(scores: list[CandidateScore]) -> DecisionPicks:
    """Apply each decision criterion; deterministic tie-break by policy_id."""
    if not scores:
        return DecisionPicks()
    nominal_best = max(scores, key=lambda c: (c.nominal_payoff, -_ord(c.policy_id))).policy_id
    maximin = max(scores, key=lambda c: (c.worst_case_payoff, -_ord(c.policy_id))).policy_id
    minimax_regret = min(scores, key=lambda c: (c.max_regret, _ord(c.policy_id))).policy_id
    most_robust = max(
        scores, key=lambda c: (c.robustness_score, c.worst_case_payoff, -_ord(c.policy_id))
    ).policy_id
    laplace = max(scores, key=lambda c: (c.mean_payoff, -_ord(c.policy_id))).policy_id
    return DecisionPicks(
        nominal_best=nominal_best,
        maximin=maximin,
        minimax_regret=minimax_regret,
        most_robust=most_robust,
        laplace=laplace,
    )


def _ord(policy_id: str) -> int:
    """Stable integer for deterministic tie-breaks (lexicographic)."""
    return sum((i + 1) * ord(ch) for i, ch in enumerate(policy_id[:16]))


def _label_for(scores: list[CandidateScore], pid: str | None) -> str:
    for c in scores:
        if c.policy_id == pid:
            return f"{c.label} ({c.policy_id})"
    return str(pid)


def _headline(scores: list[CandidateScore], picks: DecisionPicks, objective: str) -> str:
    """Say plainly whether robustness changes the choice (the demo insight)."""
    nominal = picks.nominal_best
    robust = picks.minimax_regret
    if nominal is None:
        return "No candidates evaluated."
    if nominal == robust and nominal == picks.maximin:
        return (
            f"{_label_for(scores, nominal)} wins on the headline AND is the robust "
            "choice — it stays best (or least-regret) even when the world turns "
            "against it. A rare no-trade-off pick."
        )
    if nominal == robust:
        return (
            f"{_label_for(scores, nominal)} is both the headline winner and the "
            "minimax-regret choice; the maximin (worst-case) pick differs "
            f"({_label_for(scores, picks.maximin)}), so verify the worst case."
        )
    return (
        f"Headline winner {_label_for(scores, nominal)} is NOT the robust choice: "
        f"under uncertainty, minimax-regret prefers {_label_for(scores, robust)} "
        "— the safer pick when the assumed future may not hold (SPEC §20)."
    )


__all__ = ["compare_robustness", "objective_keys"]
