"""Documented assumptions for the time-series layer (SPEC §7.2/§34).

Two kinds of knobs live here, both auditable (Estimated), never LLM-produced:

* the **synthetic-history data-generating process** — how a plausible monthly
  pre-implementation history is manufactured for a metric that the synthetic
  city has no real logs for. It is anchored to the deterministic baseline
  snapshot so the fitted forecast continues consistently from `/simulate`
  (cross-layer consistency, SPEC §34), but the path itself is clearly
  **Simulated** synthetic history, not real data;
* the **forecast model config** — smoothing / interval knobs used by the OLS
  local-linear-trend + AR(1) fit.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class TimeSeriesParams:
    """Transparent inputs to the §7.2 layer (all Estimated, not LLM outputs)."""

    # --- Synthetic history data-generating process -------------------------
    #: Months of monthly history manufactured before T0 (6 years).
    history_months: int = 72
    #: Annual seasonal period, in months.
    season_period: int = 12
    #: Underlying yearly trend of the synthetic history for VOLUME metrics
    #: (mild demand drift, consistent with the baseline projection ~1.5%/yr).
    trend_per_year: float = 0.015
    #: Relative amplitude of the annual seasonal swing for volume metrics.
    seasonal_amplitude: float = 0.06
    #: AR(1) coefficient of the synthetic noise (persistence of shocks).
    ar1_phi: float = 0.55
    #: Relative std of the AR(1) innovations (month-to-month wobble) for volumes.
    noise_rel_sigma: float = 0.02
    #: Trend/seasonality/noise are damped for SHARE (%) metrics, which are far
    #: more stable than volumes in a no-policy world.
    share_damping: float = 0.25
    #: Fixed RNG seed for the synthetic history (determinism, SPEC §34).
    seed: int = 20260813

    # --- Forecast model config --------------------------------------------
    #: Held-out tail length (months) used for an honest out-of-sample backtest.
    holdout_months: int = 12
    #: z-multipliers for the 80% and 95% prediction intervals (normal).
    z80: float = 1.2815515655446004
    z95: float = 1.959963984540054
    #: Floor on the residual std (as a fraction of the level) so a near-perfect
    #: in-sample fit still yields an honest, non-zero band.
    min_rel_sigma: float = 0.01

    def as_dict(self) -> dict:
        return asdict(self)


DEFAULT_TS_PARAMS = TimeSeriesParams()
