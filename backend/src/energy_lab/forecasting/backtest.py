"""Rolling-origin evaluation of forecasts against held-out truth."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime

from energy_lab.core.time import make_intervals, require_utc
from energy_lab.simulation.observer import ObservedRecord

from .baseline import IssuedForecast, issue_forecast


@dataclass(frozen=True, slots=True)
class BacktestFold:
    forecast: IssuedForecast
    truth_values_kw: tuple[float, ...]
    mae_kw: float
    rmse_kw: float


@dataclass(frozen=True, slots=True)
class BacktestResult:
    target: str
    method: str
    folds: tuple[BacktestFold, ...]
    mae_kw: float
    rmse_kw: float
    evaluated_intervals: int


def rolling_backtest(
    observed: tuple[ObservedRecord, ...], truth: tuple[ObservedRecord, ...], *,
    target: str, method: str, issue_times_utc: tuple[datetime, ...],
    horizon_intervals: int, site_timezone: str,
) -> BacktestResult:
    if not issue_times_utc or horizon_intervals < 1:
        raise ValueError("backtest requires issue times and positive horizon")
    truth_lookup = {(record.quantity, record.interval.start): record for record in truth}
    folds: list[BacktestFold] = []
    all_errors: list[float] = []
    for raw_issue in issue_times_utc:
        issue = require_utc(raw_issue, "backtest issue")
        intervals = make_intervals(issue, horizon_intervals, 15)
        forecast = issue_forecast(observed, target=target, method=method, issue_at_utc=issue,
                                  intervals=intervals, site_timezone=site_timezone)
        values: list[float] = []
        for interval in intervals:
            record = truth_lookup.get((target, interval.start))
            if record is None or record.interval != interval or record.unit != "kW":
                raise ValueError("held-out truth interval unavailable or not canonical kW")
            values.append(record.value)
        errors = [estimate - actual for estimate, actual in zip(forecast.values_kw, values)]
        all_errors.extend(errors)
        folds.append(BacktestFold(forecast, tuple(values), sum(abs(e) for e in errors) / len(errors),
                                  math.sqrt(sum(e * e for e in errors) / len(errors))))
    return BacktestResult(target, method, tuple(folds),
                          sum(abs(e) for e in all_errors) / len(all_errors),
                          math.sqrt(sum(e * e for e in all_errors) / len(all_errors)), len(all_errors))
