"""Observed building-load forecast benchmark with declared synthetic sensor perturbations.

This module does not infer flexible assets, grid import, or delivered response from
a single building mains meter. Held-out meter readings are used only for scoring.
"""

from __future__ import annotations

import hashlib
import math
import random
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from energy_lab.core.time import TimeInterval, make_intervals
from energy_lab.forecasting.baseline import issue_forecast
from energy_lab.simulation.observer import ObservedRecord


TARGET = "metered_building_load_kw"
METHODS = ("previous_day", "hour_day_mean", "calendar_ridge")
SEEDS = (7, 11, 19)


@dataclass(frozen=True, slots=True)
class Aggregation:
    records: tuple[ObservedRecord, ...]
    expected_intervals: int
    complete_intervals: int
    missing_or_partial_intervals: int
    invalid_source_rows: int
    duplicate_source_minutes: int


def aggregate_minutes(rows: list[tuple[str, str]], *, start_utc: datetime,
                      end_utc: datetime, quantity: str = TARGET) -> Aggregation:
    """Average exactly 15 valid one-minute W readings; never fill a missing minute."""
    if start_utc.tzinfo != timezone.utc or end_utc.tzinfo != timezone.utc or end_utc <= start_utc:
        raise ValueError("start/end must be increasing UTC instants")
    span = (end_utc - start_utc).total_seconds()
    if span % 900:
        raise ValueError("window must contain complete 15-minute intervals")
    minutes: dict[int, float] = {}
    invalid = duplicates = 0
    start_ts, end_ts = int(start_utc.timestamp()), int(end_utc.timestamp())
    for raw_timestamp, raw_watts in rows:
        # Scientific notation can discard minute precision. Do not guess its time.
        if not raw_timestamp.isdecimal():
            invalid += 1
            continue
        ts = int(raw_timestamp)
        if ts < start_ts or ts >= end_ts:
            continue
        try:
            watts = float(raw_watts)
        except ValueError:
            invalid += 1
            continue
        if ts % 60 or not math.isfinite(watts) or watts < 0:
            invalid += 1
            continue
        if ts in minutes:
            duplicates += 1
            continue
        minutes[ts] = watts
    intervals = make_intervals(start_utc, int(span // 900), 15)
    observed: list[ObservedRecord] = []
    for interval in intervals:
        ts = int(interval.start.timestamp())
        values = [minutes.get(ts + minute * 60) for minute in range(15)]
        if any(value is None for value in values):
            continue
        observed.append(ObservedRecord(interval, quantity, sum(values) / 15000, "kW"))
    return Aggregation(tuple(observed), len(intervals), len(observed),
                       len(intervals) - len(observed), invalid, duplicates)


def conditions() -> tuple[dict, ...]:
    values = [{"id": "clean", "factor": "control", "severity": 0}]
    for rate in (0.05, 0.20, 0.40):
        values.append({"id": f"missing-{int(rate * 100):02d}", "factor": "missing", "severity": rate})
    for sign in (1, -1):
        for rate in (0.02, 0.05, 0.10):
            values.append({"id": f"bias-{'plus' if sign > 0 else 'minus'}-{int(rate * 100):02d}",
                           "factor": "bias", "severity": sign * rate})
    for rate in (0.02, 0.05, 0.10):
        values.append({"id": f"noise-{int(rate * 100):02d}", "factor": "noise", "severity": rate})
    for rate in (0.01, 0.03, 0.05):
        values.append({"id": f"outliers-{int(rate * 100):02d}", "factor": "outliers", "severity": rate})
    for length in (1, 4, 12):
        values.append({"id": f"block-gap-{length}", "factor": "block_gap", "severity": length})
    return tuple(values)


def perturb_training(records: tuple[ObservedRecord, ...], *, issue_at_utc: datetime,
                     condition: dict, seed: int) -> tuple[ObservedRecord, ...]:
    """Corrupt only already observed training records for one forecast issue."""
    digest = hashlib.sha256(f"{condition['id']}:{seed}:{issue_at_utc.isoformat()}".encode()).digest()
    rng = random.Random(int.from_bytes(digest[:8], "big"))
    factor, severity = condition["factor"], condition["severity"]
    previous_day = issue_at_utc - timedelta(days=1)
    gap_start = previous_day + timedelta(hours=12)
    mean_kw = sum(item.value for item in records if item.interval.end <= issue_at_utc) / max(
        1, sum(item.interval.end <= issue_at_utc for item in records))
    changed: list[ObservedRecord] = []
    for item in records:
        if item.interval.end > issue_at_utc:
            continue
        if factor == "missing" and rng.random() < severity:
            continue
        if factor == "block_gap" and gap_start <= item.interval.start < gap_start + timedelta(minutes=15 * severity):
            continue
        value = item.value
        if factor == "bias":
            value *= 1 + severity
        elif factor == "noise":
            value = max(0.0, value + rng.gauss(0, severity * mean_kw))
        elif factor == "outliers" and rng.random() < severity:
            value *= 2
        changed.append(ObservedRecord(item.interval, item.quantity, value, item.unit))
    return tuple(changed)


def evaluate_observed_forecasts(records: tuple[ObservedRecord, ...], *,
                                issue_times_utc: tuple[datetime, ...],
                                site_timezone: str = "Asia/Kolkata") -> dict:
    """Score equal held-out 24-hour windows; failed forecasts remain abstentions."""
    lookup = {item.interval.start: item for item in records}
    if len(lookup) != len(records) or not issue_times_utc:
        raise ValueError("unique observations and issue times are required")
    rows: list[dict] = []
    for issue in issue_times_utc:
        future = make_intervals(issue, 96, 15)
        actual = tuple(lookup.get(interval.start) for interval in future)
        complete_truth = all(item is not None and item.interval == interval
                             for item, interval in zip(actual, future))
        for condition in conditions():
            for seed in (SEEDS[:1] if condition["factor"] == "control" else SEEDS):
                training = perturb_training(records, issue_at_utc=issue, condition=condition, seed=seed)
                for method in METHODS:
                    base = {"issue_at_utc": issue.isoformat(), "condition": condition["id"],
                            "factor": condition["factor"], "severity": condition["severity"],
                            "seed": seed, "method": method,
                            "training_count": len(training), "evaluated_intervals": 0,
                            "mae_kw": None, "rmse_kw": None, "absolute_peak_error_kw": None,
                            "status": "abstained", "reason": None}
                    if not complete_truth:
                        base["reason"] = "incomplete held-out meter day"
                        rows.append(base)
                        continue
                    try:
                        forecast = issue_forecast(training, target=TARGET, method=method,
                            issue_at_utc=issue, intervals=future, site_timezone=site_timezone)
                    except ValueError as exc:
                        base["reason"] = str(exc)
                        rows.append(base)
                        continue
                    errors = [predicted - item.value for predicted, item in zip(forecast.values_kw, actual)]
                    base.update({"status": "evaluated", "training_count": forecast.training_count,
                                 "evaluated_intervals": len(errors),
                                 "mae_kw": sum(abs(error) for error in errors) / len(errors),
                                 "rmse_kw": math.sqrt(sum(error * error for error in errors) / len(errors)),
                                 "absolute_peak_error_kw": abs(max(forecast.values_kw) - max(item.value for item in actual))})
                    rows.append(base)
    return {"schema_version": "1", "provenance": "observed building mains + injected synthetic sensor stress",
            "target": TARGET, "unit": "kW", "folds": rows,
            "limitations": ["No site-wide import, PV, battery, EV, pump or HVAC delivery claim is inferred.",
                            "Sensor perturbations are declared synthetic conditions, not measured fault rates.",
                            "These are forecast errors; there is no flexibility decision regret or calibrated response reliability."]}
