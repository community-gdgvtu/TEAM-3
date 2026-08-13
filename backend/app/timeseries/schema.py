"""Pydantic schemas for the §7.2 time-series forecast."""

from __future__ import annotations

from pydantic import BaseModel, Field

from ..baseline.schema import Checkpoint, MetricTag


class ForecastPoint(BaseModel):
    """A forecast value with 80% / 95% prediction intervals at one horizon."""

    t_months: float
    value: float = Field(description="Central (expected) forecast value.")
    low80: float
    high80: float
    low95: float
    high95: float


class FitDiagnostics(BaseModel):
    """The fitted structural time-series parameters — the model, made auditable."""

    level: float = Field(description="Fitted level at the last observed month.")
    slope_per_month: float = Field(description="OLS local-linear-trend slope.")
    seasonal_amplitude: float = Field(
        description="Half-range of the fitted 12-month seasonal factors."
    )
    ar1_phi: float = Field(description="Estimated AR(1) coefficient of the residuals.")
    residual_sigma: float = Field(description="Innovation std of the residual AR(1).")
    in_sample_mape_pct: float = Field(description="In-sample mean abs % error of the fit.")
    holdout_mape_pct: float | None = Field(
        default=None,
        description="Out-of-sample MAPE on a held-out tail (honest backtest); "
        "None when the series is too short to hold out.",
    )
    method: str = Field(
        default=(
            "OLS local-linear-trend + 12-month seasonal dummies, AR(1) on the "
            "residuals; prediction variance = slope-parameter uncertainty×h² + "
            "accumulated AR innovation variance (widens with horizon)."
        )
    )


class MetricForecast(BaseModel):
    """World-A and World-B forecasts for one headline metric (SPEC §7.2)."""

    key: str
    label: str
    unit: str
    is_share: bool = Field(description="True for %-share metrics (additive policy shift).")
    history_tag: MetricTag = Field(
        MetricTag.simulated,
        description="Synthetic monthly history — Simulated, not real observations.",
    )
    history: list[float] = Field(
        default_factory=list,
        description="Manufactured monthly history (oldest first), anchored to the "
        "ABM baseline snapshot at the final month.",
    )
    fit: FitDiagnostics
    world_a_tag: MetricTag = Field(
        MetricTag.estimated,
        description="Statistical baseline extrapolation — Estimated (model forecast).",
    )
    world_a: list[ForecastPoint] = Field(
        default_factory=list, description="World-A forecast across the checkpoints."
    )
    world_b_tag: MetricTag = Field(
        MetricTag.simulated,
        description="Baseline forecast shifted by the deterministic ABM policy Δ — "
        "the policy effect itself is Simulated.",
    )
    world_b: list[ForecastPoint] = Field(
        default_factory=list,
        description="World-B forecast = World-A forecast altered by the policy Δ.",
    )
    policy_shift_pct: list[float] = Field(
        default_factory=list,
        description="The ABM Δ(B−A)% applied at each checkpoint (Simulated).",
    )


class TimeSeriesForecast(BaseModel):
    """Full §7.2 payload: World A fitted & forecast first, then policy alters it."""

    provenance: MetricTag = Field(MetricTag.estimated)
    policy_id: str
    note: str = Field(
        default=(
            "Time-series layer (SPEC §7.2): World A is forecast first by a fitted "
            "structural model (local-linear-trend + seasonal + AR(1)) over a "
            "seeded synthetic history anchored to the ABM baseline; the "
            "deterministic policy Δ(B−A) then alters that baseline trajectory to "
            "give World B. Synthetic history is Simulated, the statistical "
            "forecast Estimated, the policy shift Simulated. No LLM touches any "
            "number (SPEC §7.2/§8/§34)."
        )
    )
    checkpoints: list[Checkpoint] = Field(default_factory=list)
    metrics: list[MetricForecast] = Field(default_factory=list)
    assumptions: dict = Field(
        default_factory=dict, description="Echo of the documented model assumptions."
    )
    not_modelled: list[str] = Field(
        default_factory=list,
        description="Honest scope limits of this layer (SPEC §34).",
    )
