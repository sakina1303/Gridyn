"""Fixed-seed random forest calendar comparator with strict issue-time cutoff."""

from __future__ import annotations

import math
from datetime import datetime, timedelta

from sklearn.ensemble import RandomForestRegressor

from energy_lab.core.time import TimeInterval, require_utc, site_zone
from energy_lab.simulation.observer import ObservedRecord

from .baseline import IssuedForecast, TARGETS


def _calendar_features(instant: datetime, timezone: str, lagged_value: float) -> list[float]:
    local = instant.astimezone(site_zone(timezone))
    hour = local.hour + local.minute / 60
    return [math.sin(2 * math.pi * hour / 24), math.cos(2 * math.pi * hour / 24),
            float(local.weekday()), float(local.timetuple().tm_yday), lagged_value]


def issue_tree_forecast(
    records: tuple[ObservedRecord, ...], *, target: str, issue_at_utc: datetime,
    intervals: tuple[TimeInterval, ...], site_timezone: str, seed: int,
) -> IssuedForecast:
    if target not in TARGETS:
        raise ValueError("unsupported forecast target")
    issue = require_utc(issue_at_utc, "forecast issue")
    if not intervals or intervals[0].start < issue or any(item.duration.minutes != 15 for item in intervals):
        raise ValueError("forecast needs future 15-minute intervals")
    if any(a.end != b.start for a, b in zip(intervals, intervals[1:])):
        raise ValueError("forecast intervals must be contiguous")
    training = [item for item in records if item.quantity == target and item.unit == "kW" and
                item.interval.end <= issue and item.interval.duration.minutes == 15]
    lookup: dict[datetime, float] = {}
    for item in training:
        if item.interval.start in lookup or item.value < 0:
            raise ValueError("duplicate or negative training observation")
        lookup[item.interval.start] = item.value
    if len(training) < 7 * 96:
        raise ValueError("tree comparator requires at least seven complete-day equivalents")
    x, y = [], []
    for item in training:
        lag = lookup.get(item.interval.start - timedelta(days=1))
        if lag is not None:
            x.append(_calendar_features(item.interval.start, site_timezone, lag))
            y.append(item.value)
    if len(x) < 6 * 96:
        raise ValueError("insufficient paired training observations")
    future_x = []
    for interval in intervals:
        lag = lookup.get(interval.start - timedelta(days=1))
        if lag is None:
            raise ValueError("previous-day feature unavailable at issue time")
        future_x.append(_calendar_features(interval.start, site_timezone, lag))
    model = RandomForestRegressor(n_estimators=64, max_depth=8, random_state=seed, n_jobs=1)
    model.fit(x, y)
    predictions = tuple(max(0.0, float(value)) for value in model.predict(future_x))
    return IssuedForecast(target, "random_forest", issue, max(item.interval.end for item in training),
                          len(training), intervals, predictions)
