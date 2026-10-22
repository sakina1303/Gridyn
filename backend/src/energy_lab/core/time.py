"""UTC half-open intervals and explicit IANA site-time conversion."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .units import IntervalDuration


def require_utc(value: datetime, name: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware UTC")
    if value.utcoffset() != timedelta(0):
        raise ValueError(f"{name} must be UTC, not a local offset")
    return value.astimezone(timezone.utc)


def site_zone(name: str) -> ZoneInfo:
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, TypeError, ValueError) as exc:
        raise ValueError(f"invalid IANA site timezone: {name}") from exc


def local_to_utc(local: datetime, zone_name: str, *, fold: int | None = None) -> datetime:
    """Reject missing and ambiguous civil times unless ambiguity is resolved."""
    if local.tzinfo is not None:
        raise ValueError("local datetime must be naive; pass the site timezone separately")
    zone = site_zone(zone_name)
    candidates: list[tuple[int, datetime]] = []
    for candidate_fold in (0, 1):
        aware = local.replace(tzinfo=zone, fold=candidate_fold)
        utc = aware.astimezone(timezone.utc)
        if utc.astimezone(zone).replace(tzinfo=None) == local:
            candidates.append((candidate_fold, utc))
    unique = {utc for _, utc in candidates}
    if not unique:
        raise ValueError("nonexistent local time")
    if len(unique) > 1 and fold is None:
        raise ValueError("ambiguous local time requires fold=0 or fold=1")
    if fold not in (None, 0, 1):
        raise ValueError("fold must be 0 or 1")
    if fold is None:
        return candidates[0][1]
    for candidate_fold, utc in candidates:
        if candidate_fold == fold:
            return utc
    raise ValueError("invalid fold for local time")


def utc_to_local(value: datetime, zone_name: str) -> datetime:
    return require_utc(value, "UTC datetime").astimezone(site_zone(zone_name))


@dataclass(frozen=True, slots=True)
class TimeWindow:
    start: datetime
    end: datetime

    def __post_init__(self) -> None:
        object.__setattr__(self, "start", require_utc(self.start, "window start"))
        object.__setattr__(self, "end", require_utc(self.end, "window end"))
        if self.end <= self.start:
            raise ValueError("window end must follow start")

    def contains(self, interval: TimeInterval) -> bool:
        return self.start <= interval.start and interval.end <= self.end


@dataclass(frozen=True, slots=True)
class TimeInterval:
    start: datetime
    end: datetime

    def __post_init__(self) -> None:
        object.__setattr__(self, "start", require_utc(self.start, "interval start"))
        object.__setattr__(self, "end", require_utc(self.end, "interval end"))
        if self.end <= self.start:
            raise ValueError("interval end must follow start")
        minutes = (self.end - self.start).total_seconds() / 60
        if minutes not in (15, 30, 60):
            raise ValueError("interval must be exactly 15, 30, or 60 minutes")

    @property
    def duration(self) -> IntervalDuration:
        return IntervalDuration(int((self.end - self.start).total_seconds() / 60))

    def overlaps(self, other: TimeInterval) -> bool:
        return self.start < other.end and other.start < self.end


def make_intervals(start: datetime, count: int, minutes: int) -> tuple[TimeInterval, ...]:
    start = require_utc(start, "start")
    duration = IntervalDuration(minutes)
    if isinstance(count, bool) or not isinstance(count, int) or count < 1:
        raise ValueError("count must be a positive integer")
    delta = timedelta(minutes=duration.minutes)
    return tuple(TimeInterval(start + i * delta, start + (i + 1) * delta) for i in range(count))


def validate_contiguous(intervals: tuple[TimeInterval, ...], *, required_minutes: int | None = None) -> None:
    if not intervals:
        raise ValueError("at least one interval is required")
    expected = intervals[0].duration.minutes
    if required_minutes is not None and expected != required_minutes:
        raise ValueError(f"intervals must be {required_minutes} minutes")
    for previous, current in zip(intervals, intervals[1:]):
        if current.start != previous.end or current.duration.minutes != expected:
            raise ValueError("intervals must be contiguous with one resolution")
