"""The overridable-assumption catalogue (SPEC §34.10).

Single source of truth: the *same* ``ASSUMPTIONS`` list the uncertainty engine
(§24) sweeps. Re-exporting it here (rather than re-declaring the knobs) means the
"change assumptions and rerun" surface can never disagree with what the
uncertainty fan actually perturbs — a user reads the §24 sensitivity ranking,
then pins the top assumption here and reruns, and both refer to the identical
field/default/range.

Each card is built live from :data:`app.uncertainty.engine.ASSUMPTIONS` plus the
live dataclass defaults, so the published contract cannot drift from the code
that runs (the same discipline the §33 registry uses).
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from ..baseline.params import DEFAULT_PARAMS
from ..simulation.levers import DEFAULT_SIM_PARAMS
from ..uncertainty.engine import ASSUMPTIONS, UncertainAssumption

#: Where each assumption's field lives — used to read its live default.
_DEFAULT_SOURCES = {
    "base": DEFAULT_PARAMS,
    "sim": DEFAULT_SIM_PARAMS,
}


class AssumptionCard(BaseModel):
    """One overridable model assumption a user can pin and rerun."""

    name: str = Field(description="Stable override key (send this in `overrides`).")
    label: str = Field(description="Human-readable name (matches the §24 sensitivity list).")
    target: str = Field(description="Which model the field lives on: 'base' or 'sim'.")
    field: str = Field(description="Dataclass field name the override sets.")
    unit: str = Field(default="", description="Unit of the value where meaningful.")
    default: float = Field(description="Live default read from the running dataclass.")
    low: float = Field(description="Lower edge of the documented plausible range.")
    high: float = Field(description="Upper edge of the documented plausible range.")
    provenance: str = Field(
        default="Estimated",
        description="These are input assumptions (Estimated), not observed data.",
    )


def _live_default(a: UncertainAssumption) -> float:
    """Read the assumption's default straight from the running dataclass.

    Falls back to the catalogue's declared default if the field is somehow
    absent (keeps the endpoint robust rather than 500-ing on a rename).
    """
    src = _DEFAULT_SOURCES.get(a.target)
    if src is not None and hasattr(src, a.field):
        return float(getattr(src, a.field))
    return float(a.default)


def _card(a: UncertainAssumption) -> AssumptionCard:
    return AssumptionCard(
        name=a.name,
        label=a.label,
        target=a.target,
        field=a.field,
        unit=a.unit,
        default=_live_default(a),
        low=float(a.low),
        high=float(a.high),
    )


def list_assumptions() -> list[AssumptionCard]:
    """The full catalogue of overridable assumptions, live from the code."""
    return [_card(a) for a in ASSUMPTIONS]


def assumption_index() -> dict[str, UncertainAssumption]:
    """Name → assumption spec, for validation in the service layer."""
    return {a.name: a for a in ASSUMPTIONS}
