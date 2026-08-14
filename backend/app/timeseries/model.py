"""The §7.2 structural time-series fit + forecast, then policy alters it.

Pipeline (all pure numpy, deterministic, no LLM):

1. Take the deterministic ABM baseline snapshot as the anchor for each headline
   metric, and manufacture a seeded synthetic monthly history ending there
   (:mod:`.history`).
2. **Forecast World A first** — fit a structural model to that history:
   OLS local-linear-trend + 12-month seasonal dummies, AR(1) on the residuals.
   Forecast each Time-Machine checkpoint with a prediction interval whose
   variance is *derived from the fit* — regression mean-estimation variance
   (grows with the extrapolation distance) + accumulated AR(1) innovation
   variance — so the band widens with horizon honestly (SPEC §34).
3. **Then policy models alter the baseline trajectory** (§7.2 verbatim): the
   deterministic ABM Δ(B−A) shifts the fitted World-A forecast to World B —
   multiplicatively for volumes, additively (in %-points) for shares.
"""

from __future__ import annotations

import math

import numpy as np

from ..baseline.model import compute_baseline
from ..baseline.timeseries import build_timeseries
from ..policy.dsl import PolicyDSL
from ..simulation.compare import build_delta
from ..simulation.model import compute_world_b
from ..simulation.shocks import Shocks, apply_shocks
from ..simulation.timeline import build_world_b_timeline
from .history import SHARE_KEYS, synth_history
from .params import DEFAULT_TS_PARAMS, TimeSeriesParams
from .schema import (
    Checkpoint,
    FitDiagnostics,
    ForecastPoint,
    MetricForecast,
    TimeSeriesForecast,
)

_NOT_MODELLED = [
    "Synthetic monthly history (the city keeps no real logs) — Simulated, "
    "anchored to the ABM baseline; not this city's measured observations.",
    "Single univariate model per metric — no cross-metric (VAR) or exogenous "
    "regressors beyond trend/seasonality.",
    "The policy effect comes from the ABM Δ(B−A); the time-series layer only "
    "shapes the World-A baseline trajectory and its uncertainty, not the "
    "behavioural response.",
    "Gaussian prediction intervals from the fitted variance — not a full "
    "Bayesian posterior or bootstrap.",
]


def _design_row(idx: float, period: int) -> np.ndarray:
    """Design row [1, t, seasonal dummies m=1..period-1] at (fractional) index."""
    row = np.zeros(2 + (period - 1), dtype=float)
    row[0] = 1.0
    row[1] = idx
    month = int(round(idx)) % period
    if month >= 1:
        row[1 + month] = 1.0
    return row


def _fit_series(y: np.ndarray, period: int, min_sigma: float):
    """OLS trend+seasonal fit with an AR(1) residual model.

    Returns (beta, XtX_inv, sigma_ols, phi, sigma_e, residuals, fitted).
    """
    n = y.shape[0]
    X = np.stack([_design_row(t, period) for t in range(n)])
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    fitted = X @ beta
    resid = y - fitted
    p = X.shape[1]
    dof = max(n - p, 1)
    sigma_ols = math.sqrt(float(resid @ resid) / dof)
    XtX_inv = np.linalg.pinv(X.T @ X)

    # AR(1) on residuals (mean ~0): phi = Σ r_t r_{t-1} / Σ r_{t-1}^2.
    r0, r1 = resid[:-1], resid[1:]
    denom = float(r0 @ r0)
    phi = float(r1 @ r0) / denom if denom > 1e-12 else 0.0
    phi = max(-0.98, min(0.98, phi))
    innov = r1 - phi * r0
    sigma_e = float(np.std(innov, ddof=1)) if innov.shape[0] > 1 else sigma_ols
    sigma_e = max(sigma_e, min_sigma)
    return beta, XtX_inv, sigma_ols, phi, sigma_e, resid, fitted


def _forecast_point(
    months: float,
    n: int,
    period: int,
    beta: np.ndarray,
    XtX_inv: np.ndarray,
    sigma_ols: float,
    phi: float,
    sigma_e: float,
    resid_last: float,
    params: TimeSeriesParams,
) -> tuple[float, float]:
    """Return (central value, forecast std) at ``months`` beyond T0."""
    idx = (n - 1) + months
    x0 = _design_row(idx, period)
    mean = float(x0 @ beta)
    ar_term = (phi ** months) * resid_last
    value = mean + ar_term

    # Mean-estimation variance (grows with the extrapolation distance) …
    var_param = sigma_ols * sigma_ols * float(x0 @ XtX_inv @ x0)
    # … plus accumulated AR(1) innovation variance (bounded, → σ²/(1−φ²)).
    if months <= 0:
        var_ar = 0.0
    else:
        var_ar = sigma_e * sigma_e * (1.0 - phi ** (2.0 * months)) / (1.0 - phi * phi)
    sd = math.sqrt(max(var_param + var_ar, 0.0))
    return value, sd


def run_timeseries(
    policy: PolicyDSL,
    shocks: Shocks | None = None,
    params: TimeSeriesParams = DEFAULT_TS_PARAMS,
) -> TimeSeriesForecast:
    """Forecast World A with a fitted time-series model, then apply the policy."""
    sim_params, trend = apply_shocks(shocks)

    base = compute_baseline(sim_params)
    base_ts = build_timeseries(base, trend)
    b_full = compute_world_b(policy, params=sim_params, reinvestment=True)
    b_behav = compute_world_b(policy, params=sim_params, reinvestment=False)
    b_ts = build_world_b_timeline(
        policy,
        baseline=base,
        world_b_full=b_full,
        world_b_behaviour=b_behav,
        params=sim_params,
        trend=trend,
    )
    delta = build_delta(base_ts, b_ts)

    checkpoints = [
        Checkpoint(label=cp.label, t_months=cp.t_months, t_years=cp.t_years)
        for cp in base_ts.checkpoints
    ]

    # ABM policy Δ per metric per checkpoint (absolute + %).
    delta_by_key: dict[str, dict[float, tuple[float, float | None]]] = {}
    for ds in delta.series:
        delta_by_key[ds.key] = {
            round(pt.t_months, 3): (pt.delta, pt.delta_pct) for pt in ds.points
        }

    metrics: list[MetricForecast] = []
    for m in base.metrics:
        is_share = m.key in SHARE_KEYS
        hist = synth_history(m.key, m.value, params)
        y = np.asarray(hist, dtype=float)
        n = y.shape[0]
        min_sigma = params.min_rel_sigma * abs(m.value)

        beta, XtX_inv, sigma_ols, phi, sigma_e, resid, fitted = _fit_series(
            y, params.season_period, min_sigma
        )

        # In-sample MAPE.
        nz = np.abs(y) > 1e-9
        in_mape = (
            float(np.mean(np.abs((y[nz] - fitted[nz]) / y[nz])) * 100.0)
            if nz.any()
            else 0.0
        )

        # Honest out-of-sample backtest on a held-out tail.
        holdout_mape = _holdout_mape(y, params, min_sigma)

        # Seasonal amplitude from the fitted seasonal dummies (incl. reference 0).
        seas = np.concatenate([[0.0], beta[2:]])
        seas_amp = float((seas.max() - seas.min()) / 2.0)

        fit = FitDiagnostics(
            level=round(float(fitted[-1]), 4),
            slope_per_month=round(float(beta[1]), 6),
            seasonal_amplitude=round(seas_amp, 4),
            ar1_phi=round(phi, 4),
            residual_sigma=round(sigma_e, 4),
            in_sample_mape_pct=round(in_mape, 3),
            holdout_mape_pct=(round(holdout_mape, 3) if holdout_mape is not None else None),
        )

        wa_points: list[ForecastPoint] = []
        wb_points: list[ForecastPoint] = []
        shift_pct: list[float] = []
        dmap = delta_by_key.get(m.key, {})
        for cp in checkpoints:
            value, sd = _forecast_point(
                cp.t_months, n, params.season_period, beta, XtX_inv,
                sigma_ols, phi, sigma_e, float(resid[-1]), params,
            )
            wa = ForecastPoint(
                t_months=cp.t_months,
                value=round(value, 4),
                low80=round(value - params.z80 * sd, 4),
                high80=round(value + params.z80 * sd, 4),
                low95=round(value - params.z95 * sd, 4),
                high95=round(value + params.z95 * sd, 4),
            )
            wa_points.append(wa)

            d_abs, d_pct = dmap.get(round(cp.t_months, 3), (0.0, 0.0))
            if is_share:
                # Additive %-point shift; band shifts with the level.
                factor_add = d_abs
                wb_val = value + factor_add
                wb = ForecastPoint(
                    t_months=cp.t_months,
                    value=round(wb_val, 4),
                    low80=round(wa.low80 + factor_add, 4),
                    high80=round(wa.high80 + factor_add, 4),
                    low95=round(wa.low95 + factor_add, 4),
                    high95=round(wa.high95 + factor_add, 4),
                )
                shift_pct.append(round(d_pct if d_pct is not None else 0.0, 3))
            else:
                # Multiplicative shift by the ABM Δ%.
                if d_pct is not None:
                    factor = 1.0 + d_pct / 100.0
                elif abs(value) > 1e-9:
                    factor = 1.0 + d_abs / value
                else:
                    factor = 1.0
                wb = ForecastPoint(
                    t_months=cp.t_months,
                    value=round(value * factor, 4),
                    low80=round(wa.low80 * factor, 4),
                    high80=round(wa.high80 * factor, 4),
                    low95=round(wa.low95 * factor, 4),
                    high95=round(wa.high95 * factor, 4),
                )
                shift_pct.append(round((factor - 1.0) * 100.0, 3))
            wb_points.append(wb)

        metrics.append(
            MetricForecast(
                key=m.key,
                label=m.label,
                unit=m.unit,
                is_share=is_share,
                history=[round(v, 4) for v in hist],
                fit=fit,
                world_a=wa_points,
                world_b=wb_points,
                policy_shift_pct=shift_pct,
            )
        )

    return TimeSeriesForecast(
        policy_id=policy.id,
        checkpoints=checkpoints,
        metrics=metrics,
        assumptions=params.as_dict(),
        not_modelled=_NOT_MODELLED,
    )


def _holdout_mape(
    y: np.ndarray, params: TimeSeriesParams, min_sigma: float
) -> float | None:
    """Refit on all but the last ``holdout_months`` and score the forecast MAPE."""
    h = params.holdout_months
    n = y.shape[0]
    if h <= 0 or n - h < 2 * params.season_period:
        return None
    y_train = y[: n - h]
    y_test = y[n - h :]
    n_train = y_train.shape[0]
    beta, XtX_inv, sigma_ols, phi, sigma_e, resid, _ = _fit_series(
        y_train, params.season_period, min_sigma
    )
    errs = []
    for k in range(1, h + 1):
        value, _ = _forecast_point(
            float(k), n_train, params.season_period, beta, XtX_inv,
            sigma_ols, phi, sigma_e, float(resid[-1]), params,
        )
        actual = float(y_test[k - 1])
        if abs(actual) > 1e-9:
            errs.append(abs((actual - value) / actual))
    return float(np.mean(errs) * 100.0) if errs else None
