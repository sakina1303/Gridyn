"""Simple 15-minute forecasts issued from observations available by a cutoff."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta

from energy_lab.core.time import TimeInterval, require_utc, site_zone
from energy_lab.core.units import finite_number
from energy_lab.simulation.observer import ObservedRecord


TARGETS = frozenset({"pv_available_kw", "critical_load_kw", "fixed_load_kw"})
METHODS = frozenset({"previous_day", "previous_week", "hour_day_mean", "calendar_ridge"})


@dataclass(frozen=True, slots=True)
class IssuedForecast:
    target: str
    method: str
    issued_at_utc: datetime
    training_end_utc: datetime
    training_count: int
    intervals: tuple[TimeInterval, ...]
    values_kw: tuple[float, ...]
    unit: str = "kW"


def _features(instant: datetime, timezone: str) -> tuple[float, ...]:
    local = instant.astimezone(site_zone(timezone))
    hour = local.hour + local.minute / 60
    angle = 2 * math.pi * hour / 24
    return (1.0, math.sin(angle), math.cos(angle),
            1.0 if local.weekday() < 5 else 0.0)


def _solve_linear(matrix: list[list[float]], rhs: list[float]) -> list[float]:
    """Small pivoted Gaussian solve for a four-feature ridge model."""
    n = len(rhs)
    aug = [matrix[i][:] + [rhs[i]] for i in range(n)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda row: abs(aug[row][col]))
        if abs(aug[pivot][col]) < 1e-12:
            raise ValueError("calendar ridge matrix is singular")
        aug[col], aug[pivot] = aug[pivot], aug[col]
        scale = aug[col][col]
        aug[col] = [value / scale for value in aug[col]]
        for row in range(n):
            if row == col:
                continue
            factor = aug[row][col]
            aug[row] = [value - factor * base for value, base in zip(aug[row], aug[col])]
    return [row[-1] for row in aug]


def issue_forecast(
    records: tuple[ObservedRecord, ...], *, target: str, method: str,
    issue_at_utc: datetime, intervals: tuple[TimeInterval, ...], site_timezone: str,
) -> IssuedForecast:
    if target not in TARGETS or method not in METHODS:
        raise ValueError("unsupported forecast target or method")
    issue = require_utc(issue_at_utc, "forecast issue")
    site_zone(site_timezone)
    if not intervals or intervals[0].start < issue:
        raise ValueError("forecast intervals must begin at or after issue time")
    if any(interval.duration.minutes != 15 for interval in intervals):
        raise ValueError("forecast requires 15-minute intervals")
    if any(a.end != b.start for a, b in zip(intervals, intervals[1:])):
        raise ValueError("forecast intervals must be contiguous")
    training = [record for record in records if record.quantity == target and
                record.unit == "kW" and record.interval.end <= issue and
                record.interval.duration.minutes == 15]
    if not training:
        raise ValueError("no usable target observations available by issue time")
    lookup: dict[datetime, float] = {}
    for record in training:
        if record.interval.start in lookup:
            raise ValueError("duplicate training interval")
        lookup[record.interval.start] = finite_number(record.value, "training value")
        if record.value < 0:
            raise ValueError("negative gross target observation")
    training.sort(key=lambda record: record.interval.start)
    values: list[float] = []
    if method in {"previous_day", "previous_week"}:
        lag = timedelta(days=1 if method == "previous_day" else 7)
        for interval in intervals:
            key = interval.start - lag
            if key not in lookup:
                raise ValueError(f"{method} observation unavailable for {interval.start.isoformat()}")
            values.append(lookup[key])
    elif method == "hour_day_mean":
        buckets: dict[tuple[int, int, int], list[float]] = {}
        for record in training:
            local = record.interval.start.astimezone(site_zone(site_timezone))
            key = (local.weekday() < 5, local.hour, local.minute)
            buckets.setdefault(key, []).append(record.value)
        for interval in intervals:
            local = interval.start.astimezone(site_zone(site_timezone))
            key = (local.weekday() < 5, local.hour, local.minute)
            peers = buckets.get(key)
            if not peers:
                raise ValueError("hour/day peers unavailable for forecast interval")
            values.append(sum(peers) / len(peers))
    else:
        if len(training) < 16:
            raise ValueError("calendar ridge requires at least 16 observed intervals")
        xs = [_features(record.interval.start, site_timezone) for record in training]
        ys = [record.value for record in training]
        size = len(xs[0])
        matrix = [[sum(x[i] * x[j] for x in xs) + (0.0 if i != j else (0.0 if i == 0 else 1.0))
                   for j in range(size)] for i in range(size)]
        rhs = [sum(x[i] * y for x, y in zip(xs, ys)) for i in range(size)]
        weights = _solve_linear(matrix, rhs)
        values = [max(0.0, sum(weight * feature for weight, feature in zip(weights, _features(interval.start, site_timezone))))
                  for interval in intervals]
    return IssuedForecast(target, method, issue, max(record.interval.end for record in training),
                          len(training), intervals, tuple(values))
