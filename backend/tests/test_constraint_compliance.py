"""Stated-constraint compliance in the distributional microsim (SPEC §7.3/§34).

A policy can declare ``constraints.max_low_income_burden_increase_pct`` — a hard
cap the minister sets on how much the charge may raise low-income households' cost
burden. The rule compiler and the LLM both extract it, it is echoed as a reviewable
assumption, and the Equity Advocate persona even argues it "must be monitored
against the modelled distributional outcome, not just asserted" — yet nothing ever
tested it against the numbers. A constraint you never check is theatre (SPEC §34).

These tests pin the honest behaviour: the microsim now computes the modelled
low-income burden and reports whether the policy satisfies or violates its own
declared cap, with the numbers and margin, and stays silent (``None``) when no
constraint is declared so every existing policy is unchanged.
"""

from __future__ import annotations

from app.microsim.model import build_microsim_report
from app.policy.dsl import (
    Constraints,
    Intervention,
    InterventionType,
    PolicyDSL,
)
from app.policy.rules import parse_policy


def _charge(cap: float | None = None, exemptions: list[str] | None = None) -> PolicyDSL:
    return PolicyDSL(
        intervention=Intervention(
            type=InterventionType.road_pricing, amount=10.0, currency="GBP"
        ),
        exemptions=exemptions or [],
        constraints=Constraints(max_low_income_burden_increase_pct=cap),
    )


def test_no_constraint_declared_leaves_check_absent() -> None:
    # Every existing policy (no declared cap) is unchanged: the field stays null.
    report = build_microsim_report(_charge(cap=None))
    assert report.constraint_check is None


def test_satisfied_constraint_reports_headroom() -> None:
    report = build_microsim_report(_charge(cap=1.0))
    check = report.constraint_check
    assert check is not None
    assert check.name == "max_low_income_burden_increase_pct"
    assert check.cap_pct == 1.0
    assert check.satisfied is True
    # The modelled burden equals the lowest-income decile's mean burden %.
    assert check.modelled_low_income_burden_pct == report.by_income_decile[0].mean_burden_pct_income
    # Margin = cap − modelled, positive when there is headroom.
    assert abs(check.margin_pct - (check.cap_pct - check.modelled_low_income_burden_pct)) < 1e-6
    assert check.margin_pct > 0


def test_violated_constraint_is_flagged_not_hidden() -> None:
    # A cap tighter than the modelled burden must read as a violation, honestly.
    report = build_microsim_report(_charge(cap=0.1))
    check = report.constraint_check
    assert check is not None
    assert check.modelled_low_income_burden_pct > check.cap_pct
    assert check.satisfied is False
    assert check.margin_pct < 0
    assert "violates" in check.note.lower()


def test_low_income_exemption_satisfies_any_cap() -> None:
    # Exempting low-income commuters drives their modelled cordon burden to zero,
    # so even a near-zero cap holds — the honest reward for designing the exemption.
    report = build_microsim_report(_charge(cap=0.1, exemptions=["low-income"]))
    check = report.constraint_check
    assert check is not None
    assert check.modelled_low_income_burden_pct == 0.0
    assert check.satisfied is True
    assert check.margin_pct == check.cap_pct


def test_check_is_reachable_from_natural_language() -> None:
    # The rule compiler extracts the cap, so the whole path works without an LLM.
    dsl, _ = parse_policy(
        "Charge £10 to enter the centre, but the burden on low-income households "
        "must not rise by more than 2%."
    )
    assert dsl.constraints.max_low_income_burden_increase_pct == 2.0
    report = build_microsim_report(dsl)
    assert report.constraint_check is not None
    assert report.constraint_check.cap_pct == 2.0


def test_compliance_provenance_is_simulated() -> None:
    report = build_microsim_report(_charge(cap=5.0))
    assert report.constraint_check.provenance.value == "Simulated"
