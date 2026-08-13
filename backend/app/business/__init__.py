"""Business View — per-firm "click a firm" drill-down (SPEC §17 Business View).

The micro counterpart to the Citizen View. SPEC §17 asks for a firm-level view —
footfall, labour accessibility, deliveries, costs, revenue proxy, adaptation
decisions — so the model is explainable at both macro and micro levels. This
layer answers exactly that for one synthetic firm (a commercial building), reusing
the same deterministic mode-choice model as ``/simulate`` (for its workers' labour
accessibility) and the same economic coefficients as ``/economy`` (for footfall /
deliveries / cost / revenue), staged over the Time Machine — so a firm's numbers
can never disagree with the aggregates beside them. No LLM in the numeric path
(SPEC §34).
"""

from .service import (
    FirmNotFound,
    build_business_view,
    sample_firms,
)
from .schema import (
    BusinessView,
    FirmProfile,
    FirmSample,
    FirmSnapshot,
)

__all__ = [
    "build_business_view",
    "sample_firms",
    "FirmNotFound",
    "BusinessView",
    "FirmProfile",
    "FirmSnapshot",
    "FirmSample",
]
