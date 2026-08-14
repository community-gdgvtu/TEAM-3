"""Time-series forecast layer (SPEC §7.2).

The one enumerated SPEC §7 hybrid-forecast sub-layer that had no dedicated
implementation. The existing :mod:`app.baseline.timeseries` carries the World-A
snapshot forward with a *fixed* exogenous growth assumption and a hand-set
widening band — useful as a dashboard reference, but it is **not** a fitted
statistical time-series model.

SPEC §7.2 asks for the layer that treats variables *whose temporal structure is
informative*: dynamic regression / state-space / structural time series. It says
plainly: **"Forecast World A first. Then policy models alter the baseline
trajectory."**

This package delivers exactly that, in pure numpy:

* a transparent, seeded **synthetic monthly history** for each headline metric
  (documented DGP: trend + annual seasonality + AR(1) noise), anchored so its
  final observation equals the deterministic ABM baseline snapshot — labelled
  **Simulated** synthetic history, never claimed to be real observations;
* a **structural time-series fit** (OLS local-linear-trend + seasonal dummies,
  AR(1) on the residuals) that forecasts **World A** forward with prediction
  intervals whose variance is *derived from the fit* (slope-parameter
  uncertainty × horizon² + accumulated AR innovation variance) and therefore
  **widens with horizon** honestly (SPEC §34), not by a pasted-on assumption;
* the policy step: the deterministic ABM Δ(B−A)% shifts the fitted baseline
  trajectory to give **World B** — "policy models alter the baseline
  trajectory" verbatim.

Provenance: synthetic history **Simulated**, the statistical baseline forecast
**Estimated** (model extrapolation), the policy shift **Simulated** (from the
ABM). No LLM touches any number (SPEC §7.2/§8/§34).
"""

from .model import run_timeseries
from .params import DEFAULT_TS_PARAMS, TimeSeriesParams
from .schema import TimeSeriesForecast

__all__ = [
    "run_timeseries",
    "TimeSeriesForecast",
    "TimeSeriesParams",
    "DEFAULT_TS_PARAMS",
]
