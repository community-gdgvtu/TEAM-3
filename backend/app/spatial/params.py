"""Transparent assumptions for the spatial traffic-assignment layer (SPEC §7.7).

Every constant here is an **input assumption** (Estimated), never an observed
record and never an LLM output. They parameterise the deterministic static
traffic-assignment model in :mod:`app.spatial.assignment` and the accessibility /
pollution proxies in :mod:`app.spatial.model`. Keeping them in one auditable place
lets the Evidence Drawer (SPEC §26) and the model registry (SPEC §33) surface
exactly which assumption fed which spatial number.

Guardrail (SPEC §34): these constants and the code that consumes them produce
core numeric spatial effects deterministically. No LLM is involved.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from ..baseline.params import DEFAULT_PARAMS


@dataclass(frozen=True)
class SpatialParams:
    """Assumptions for the peak-hour road-network assignment (SPEC §7.7)."""

    # --- Demand: commuters → peak-hour vehicles ----------------------------
    #: Fraction of a car commuter's inbound (home→work) commute trip that falls
    #: in the single busiest hour. Concentrates daily flow into a peak-hour load
    #: that is comparable with the link ``capacity_veh_per_hr``.
    peak_hour_share: float = 0.42
    #: Average car occupancy (persons per vehicle) — converts commuter person
    #: trips to vehicle trips on the network.
    car_occupancy: float = 1.2

    # --- Volume-delay (BPR) function ---------------------------------------
    # Congested link time t = t0 · (1 + α·(v/c)^β). α, β are the standard US
    # Bureau of Public Roads defaults — a documented, widely-used approximation.
    bpr_alpha: float = 0.15
    bpr_beta: float = 4.0

    # --- Equilibrium assignment --------------------------------------------
    #: Method-of-Successive-Averages iterations. The network is tiny (81 nodes)
    #: so this converges quickly toward a static user equilibrium.
    assignment_iterations: int = 25

    # --- Accessibility (gravity job accessibility) -------------------------
    #: Impedance decay per minute of congested car travel time. A_i =
    #: Σ_j jobs_j · exp(−decay · time_ij). Higher = accessibility falls off
    #: faster with travel time.
    access_decay_per_min: float = 0.08

    # --- Pollution dispersion proxy ----------------------------------------
    #: Share of a zone's locally-emitted road CO₂ spread to its immediate grid
    #: neighbours (a crude dispersion smoothing, NOT a physical plume model).
    pollution_neighbour_share: float = 0.25
    #: Tailpipe CO₂ per vehicle-km — reused from the baseline so the spatial
    #: emissions proxy is consistent with the aggregate emissions metric.
    co2_kg_per_veh_km: float = DEFAULT_PARAMS.car_co2_kg_per_km

    def as_dict(self) -> dict:
        return asdict(self)


#: Default spatial assumptions used unless a caller overrides them.
DEFAULT_SPATIAL_PARAMS = SpatialParams()
