"""Backtesting endpoint (ROADMAP stretch, SPEC §25).

* ``GET /backtest/example`` — the built-in synthetic benchmark case.
* ``POST /backtest`` — replay a supplied :class:`HistoricalCase` (or, if none is
  given, the built-in example) and return the scorecard.

The forecast is Simulated; the scores are exact arithmetic; no LLM is on the
numeric path (SPEC §25/§34). The built-in case's actuals are a clearly-labelled
synthetic benchmark, not real observations.
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from ..backtest import HistoricalCase, Scorecard, example_case, run_backtest
from ..simulation.shocks import Shocks

router = APIRouter(prefix="/backtest", tags=["backtest"])


class BacktestRequest(BaseModel):
    """Input to ``POST /backtest``."""

    case: HistoricalCase | None = Field(
        default=None,
        description="Historical case to replay. If omitted, the built-in synthetic "
        "benchmark case is used.",
    )
    shocks: Shocks | None = Field(default=None, description="Optional exogenous stressors.")


@router.get("/example", response_model=HistoricalCase, summary="Built-in benchmark case")
def example() -> HistoricalCase:
    """Return the built-in synthetic benchmark historical case."""
    return example_case()


@router.post("", response_model=Scorecard, summary="Replay a case → scorecard")
def backtest(req: BacktestRequest) -> Scorecard:
    """Replay the supplied (or built-in) case and score the forecast (SPEC §25)."""
    case = req.case or example_case()
    return run_backtest(case, shocks=req.shocks)
