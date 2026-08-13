"""Deterministic synthetic monthly history for the §7.2 layer.

The synthetic city keeps no real time-logs, so §7.2 (which fits a model to a
historical series) needs a history to fit. We manufacture one from a documented
data-generating process — trend + annual seasonality + AR(1) noise — seeded so
it is byte-reproducible (SPEC §34), then **anchor** it so the final month equals
the deterministic ABM baseline value for that metric. The anchor is what keeps
the §7.2 forecast continuous with `/simulate`'s World-A snapshot; the series
itself is honestly **Simulated** synthetic history, not real observations.
"""

from __future__ import annotations

import math

import numpy as np

from .params import TimeSeriesParams


# Metric keys that are *shares* (percentages), not volumes — their synthetic
# history is far more stable (damped trend / seasonality / noise).
SHARE_KEYS = frozenset(
    {
        "mode_share.car_pct",
        "mode_share.public_transit_pct",
        "mode_share.walk_pct",
    }
)


def _metric_seed(base_seed: int, key: str) -> int:
    """A stable per-metric seed so each series is independent yet reproducible."""
    h = 0
    for ch in key:
        h = (h * 131 + ord(ch)) & 0xFFFFFFFF
    return (base_seed ^ h) & 0x7FFFFFFF


def synth_history(
    key: str, anchor_value: float, params: TimeSeriesParams
) -> list[float]:
    """Manufacture a monthly history ending at ``anchor_value`` (last month).

    Returns ``history_months`` values, oldest first, the last equal to the ABM
    baseline snapshot value for ``key``. Deterministic given ``params.seed``.
    """
    n = params.history_months
    period = params.season_period
    is_share = key in SHARE_KEYS
    damp = params.share_damping if is_share else 1.0

    rng = np.random.default_rng(_metric_seed(params.seed, key))

    trend_per_month = (params.trend_per_year * damp) / 12.0
    seas_amp = params.seasonal_amplitude * damp
    phi = params.ar1_phi
    innov_sigma = params.noise_rel_sigma * damp

    # Build a relative path around 1.0: deterministic trend + seasonal + AR(1).
    ar = 0.0
    rel = np.empty(n, dtype=float)
    for t in range(n):
        # Trend measured backward from the final (anchor) month so the newest
        # month sits near the top of the mild upward drift.
        months_before_end = n - 1 - t
        trend = -trend_per_month * months_before_end
        seasonal = seas_amp * math.sin(2.0 * math.pi * (t % period) / period)
        ar = phi * ar + rng.normal(0.0, innov_sigma)
        rel[t] = 1.0 + trend + seasonal + ar

    # Anchor: rescale so the last month equals the ABM baseline value exactly.
    rel *= anchor_value / rel[-1]
    return [float(v) for v in rel]
