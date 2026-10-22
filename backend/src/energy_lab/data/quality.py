"""Auditable quality metrics on canonical, unmodified observed records."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from statistics import median

from energy_lab.core.time import TimeWindow, make_intervals, require_utc, site_zone
from energy_lab.core.units import IntervalDuration, nonnegative
from energy_lab.simulation.observer import ObservedRecord

from .ingest import ENERGY_STATE_SIGNALS, POWER_SIGNALS, TEMPERATURE_SIGNALS


@dataclass(frozen=True, slots=True)
class QualityIssue:
    code: str
    severity: str  # warning, insufficient, invalid
    quantity: str | None
    interval_indices: tuple[int, ...]
    detail: str


@dataclass(frozen=True, slots=True)
class SeriesQuality:
    quantity: str
    expected_count: int
    observed_count: int
    valid_count: int
    coverage: float
    missing_count: int
    longest_gap_intervals: int
    resolution_minutes: int
    status: str


@dataclass(frozen=True, slots=True)
class DataQualityReport:
    expected_window: TimeWindow
    declared_resolution_minutes: int
    site_timezone: str
    series: tuple[SeriesQuality, ...]
    issues: tuple[QualityIssue, ...]

    def for_quantity(self, quantity: str) -> SeriesQuality | None:
        return next((item for item in self.series if item.quantity == quantity), None)


def _longest_run(indices: set[int]) -> int:
    best = current = 0
    previous = None
    for index in sorted(indices):
        current = current + 1 if previous is not None and index == previous + 1 else 1
        best = max(best, current)
        previous = index
    return best


def assess_quality(
    records: tuple[ObservedRecord, ...],
    *,
    expected_start_utc: datetime,
    expected_end_utc: datetime,
    declared_resolution_minutes: int,
    site_timezone: str,
    site_rating_kw: float,
    pv_capacity_kw: float | None = None,
) -> DataQualityReport:
    start = require_utc(expected_start_utc, "expected start")
    end = require_utc(expected_end_utc, "expected end")
    window = TimeWindow(start, end)
    site_zone(site_timezone)
    duration = IntervalDuration(declared_resolution_minutes)
    nonnegative(site_rating_kw, "site rating kW")
    if pv_capacity_kw is not None:
        nonnegative(pv_capacity_kw, "PV capacity kW")
    count_float = (end - start).total_seconds() / (duration.minutes * 60)
    if not count_float.is_integer():
        raise ValueError("expected window must be an integer number of declared intervals")
    expected = make_intervals(start, int(count_float), duration.minutes)
    expected_lookup = {(interval.start, interval.end): index for index, interval in enumerate(expected)}
    groups: dict[str, list[ObservedRecord]] = {}
    for record in records:
        groups.setdefault(record.quantity, []).append(record)
    issues: list[QualityIssue] = []
    summaries: list[SeriesQuality] = []
    valid_by_key: dict[tuple[str, int], float] = {}
    for quantity, group in sorted(groups.items()):
        series_issues: list[QualityIssue] = []
        unique: dict[int, ObservedRecord] = {}
        seen_intervals: set[tuple[datetime, datetime]] = set()
        for record in group:
            key = (record.interval.start, record.interval.end)
            index = expected_lookup.get(key)
            if key in seen_intervals:
                series_issues.append(QualityIssue("duplicate", "invalid", quantity, (index,) if index is not None else (), "duplicate interval"))
                continue
            seen_intervals.add(key)
            if index is None:
                series_issues.append(QualityIssue("off_grid_timestamp", "invalid", quantity, (), "interval is outside or misaligned with declared grid"))
                continue
            expected_unit = "kW" if quantity in POWER_SIGNALS else "kWh" if quantity in ENERGY_STATE_SIGNALS else "°C" if quantity in TEMPERATURE_SIGNALS else None
            if expected_unit is None or record.unit != expected_unit:
                series_issues.append(QualityIssue("unit_mismatch", "invalid", quantity, (index,), f"expected {expected_unit or 'known quantity'}"))
                continue
            if quantity in POWER_SIGNALS | ENERGY_STATE_SIGNALS and record.value < 0:
                series_issues.append(QualityIssue("negative_gross_value", "invalid", quantity, (index,), "gross physical value must be nonnegative"))
                continue
            if quantity in {"pv_available_kw", "pv_used_kw"} and pv_capacity_kw is not None and record.value > pv_capacity_kw:
                series_issues.append(QualityIssue("pv_above_capacity", "invalid", quantity, (index,), "PV exceeds configured AC capacity"))
                continue
            unique[index] = record
            valid_by_key[(quantity, index)] = record.value

        missing = set(range(len(expected))) - set(unique)
        coverage = len(unique) / len(expected)
        if missing:
            series_issues.append(QualityIssue("missing_intervals", "warning", quantity, tuple(sorted(missing)), f"{len(missing)} expected intervals absent or invalid"))
        if coverage < 0.80:
            series_issues.append(QualityIssue("low_coverage", "insufficient", quantity, (), "coverage below provisional 80% forecast gate"))
        elif coverage < 0.95:
            series_issues.append(QualityIssue("limited_coverage", "warning", quantity, (), "coverage below provisional 95% review gate"))

        # Compare the same local hour across multiple days; never remove flagged values.
        hourly: dict[int, list[tuple[int, float]]] = {}
        zone = site_zone(site_timezone)
        for index, record in unique.items():
            local_hour = record.interval.start.astimezone(zone).hour
            hourly.setdefault(local_hour, []).append((index, record.value))
        for peers in hourly.values():
            if len(peers) < 7:
                continue
            center = median(value for _, value in peers)
            mad = median(abs(value - center) for _, value in peers)
            if mad <= 0:
                continue
            for index, value in peers:
                if abs(value - center) > 5 * mad:
                    series_issues.append(QualityIssue("possible_outlier", "warning", quantity, (index,), "greater than 5× peer-hour MAD; retained"))

        status = "invalid" if any(issue.severity == "invalid" for issue in series_issues) else (
            "insufficient" if coverage < 0.80 else "usable_with_limitations" if series_issues else "usable"
        )
        summaries.append(SeriesQuality(quantity, len(expected), len(group), len(unique), coverage,
                                       len(missing), _longest_run(missing), duration.minutes, status))
        issues.extend(series_issues)

    # Cross-signal balance is only checkable when *all* flow signals are observed.
    required = {"pv_used_kw", "grid_import_kw", "grid_export_kw", "battery_charge_kw",
                "battery_discharge_kw", "critical_load_kw", "fixed_load_kw", "flexible_load_kw"}
    if required.issubset(groups):
        bad_streak: list[int] = []
        threshold = max(2.0, 0.02 * site_rating_kw)
        for index in range(len(expected)):
            if all((quantity, index) in valid_by_key for quantity in required):
                value = lambda quantity: valid_by_key[(quantity, index)]
                residual = value("pv_used_kw") + value("grid_import_kw") + value("battery_discharge_kw") - (
                    value("critical_load_kw") + value("fixed_load_kw") + value("flexible_load_kw") +
                    value("battery_charge_kw") + value("grid_export_kw")
                )
                if abs(residual) > threshold:
                    bad_streak.append(index)
                    continue
            if len(bad_streak) >= 4:
                issues.append(QualityIssue("cross_signal_imbalance", "warning", None, tuple(bad_streak), "sustained measured balance mismatch; inspect meter timing and unmodeled loads"))
            bad_streak = []
        if len(bad_streak) >= 4:
            issues.append(QualityIssue("cross_signal_imbalance", "warning", None, tuple(bad_streak), "sustained measured balance mismatch; inspect meter timing and unmodeled loads"))

    return DataQualityReport(window, duration.minutes, site_timezone, tuple(summaries), tuple(issues))
