"""Seeded synthetic *exogenous truth* for a campus archetype.

These profiles are illustrative engineering assumptions, never measured Indian data.
The generator does not choose an operating schedule or simulate its resulting flows.
"""

from __future__ import annotations

import math
import platform
import random
from dataclasses import dataclass, replace
from datetime import datetime, time, timedelta

from energy_lab.core.assets import EVConfig, SiteConfig
from energy_lab.core.time import TimeWindow, local_to_utc, make_intervals, require_utc, utc_to_local
from energy_lab.core.units import finite_number, nonnegative
from energy_lab.data.manifest import canonical_sha256, named_seed

from .engine import TruthDisturbance


GENERATOR_VERSION = "0.1.0"
CANONICAL_MODEL_VERSION = "46-v1"


@dataclass(frozen=True, slots=True)
class EVBehavior:
    sessions_per_day: int
    charger_power_kw: float
    min_required_kwh: float
    max_required_kwh: float
    arrival_hour_local: int = 9
    departure_hour_local: int = 18
    jitter_intervals: int = 2
    charger_efficiency: float = 1.0

    def __post_init__(self) -> None:
        if isinstance(self.sessions_per_day, bool) or not isinstance(self.sessions_per_day, int) or self.sessions_per_day < 0:
            raise ValueError("sessions_per_day must be a nonnegative integer")
        if self.sessions_per_day and self.charger_power_kw <= 0:
            raise ValueError("EV charger power must be positive")
        nonnegative(self.charger_power_kw, "EV charger power kW")
        nonnegative(self.min_required_kwh, "minimum EV energy kWh")
        nonnegative(self.max_required_kwh, "maximum EV energy kWh")
        if self.min_required_kwh > self.max_required_kwh:
            raise ValueError("minimum EV energy exceeds maximum")
        if not (0 <= self.arrival_hour_local < self.departure_hour_local <= 23):
            raise ValueError("EV local arrival/departure hours must define a same-day window")
        if isinstance(self.jitter_intervals, bool) or not isinstance(self.jitter_intervals, int) or self.jitter_intervals < 0:
            raise ValueError("jitter_intervals must be a nonnegative integer")
        if not 0 < self.charger_efficiency <= 1:
            raise ValueError("EV charger efficiency must be in (0,1]")


@dataclass(frozen=True, slots=True)
class GenerationConfig:
    dataset_id: str
    site: SiteConfig
    start_utc: datetime
    interval_count: int
    root_seed: int
    weather_scenario: str = "clear"
    load_scenario: str = "normal"
    solar_scenario: str = "standard"
    critical_base_kw: float = 30.0
    fixed_base_kw: float = 45.0
    day_activity_kw: float = 45.0
    evening_activity_kw: float = 20.0
    cooling_kw_per_c_above_28: float = 2.0
    ev_behavior: EVBehavior | None = None
    synthetic_tariff_inr_per_kwh: float | None = None

    def __post_init__(self) -> None:
        if not self.dataset_id:
            raise ValueError("dataset_id is required")
        require_utc(self.start_utc, "generation start")
        if isinstance(self.interval_count, bool) or not isinstance(self.interval_count, int) or self.interval_count < 1:
            raise ValueError("interval_count must be a positive integer")
        named_seed(self.root_seed, "validation")
        if self.weather_scenario not in {"clear", "cloudy", "monsoon_like"}:
            raise ValueError("unsupported weather scenario")
        if self.load_scenario not in {"normal", "high_cooling", "low_activity"}:
            raise ValueError("unsupported load scenario")
        if self.solar_scenario not in {"standard", "low", "high"}:
            raise ValueError("unsupported solar scenario")
        for name in ("critical_base_kw", "fixed_base_kw", "day_activity_kw", "evening_activity_kw", "cooling_kw_per_c_above_28"):
            nonnegative(getattr(self, name), name)
        if self.synthetic_tariff_inr_per_kwh is not None:
            finite_number(self.synthetic_tariff_inr_per_kwh, "synthetic tariff INR/kWh")
        if self.ev_behavior is not None and self.site.evs:
            raise ValueError("generated EV sessions and configured EV assets cannot be combined")


@dataclass(frozen=True, slots=True)
class TruthManifest:
    dataset_id: str
    generator_version: str
    canonical_model_version: str
    config_sha256: str
    truth_sha256: str
    root_seed: int
    stream_seeds: tuple[tuple[str, int], ...]
    python_version: str
    interval_minutes: int
    site_timezone: str
    start_utc: datetime
    interval_count: int
    synthetic: bool = True


@dataclass(frozen=True, slots=True)
class GeneratedTruth:
    site: SiteConfig
    disturbances: tuple[TruthDisturbance, ...]
    manifest: TruthManifest


def _make_ev_sessions(config: GenerationConfig, rng: random.Random, horizon_end: datetime) -> tuple[EVConfig, ...]:
    behavior = config.ev_behavior
    if behavior is None or behavior.sessions_per_day == 0:
        return config.site.evs
    intervals = make_intervals(config.start_utc, config.interval_count, 15)
    dates = sorted({utc_to_local(interval.start, config.site.timezone).date() for interval in intervals})
    sessions: list[EVConfig] = []
    for day in dates:
        for index in range(behavior.sessions_per_day):
            arrival_shift = rng.randint(-behavior.jitter_intervals, behavior.jitter_intervals)
            departure_shift = rng.randint(-behavior.jitter_intervals, behavior.jitter_intervals)
            arrival_local = datetime.combine(day, time(behavior.arrival_hour_local)) + timedelta(minutes=15 * arrival_shift)
            departure_local = datetime.combine(day, time(behavior.departure_hour_local)) + timedelta(minutes=15 * departure_shift)
            arrival = local_to_utc(arrival_local, config.site.timezone)
            departure = local_to_utc(departure_local, config.site.timezone)
            if arrival < config.start_utc or departure > horizon_end or departure <= arrival:
                continue
            max_feasible = behavior.charger_power_kw * behavior.charger_efficiency * (departure - arrival).total_seconds() / 3600
            if max_feasible < behavior.min_required_kwh:
                raise ValueError("generated EV window cannot satisfy minimum required energy")
            requested = rng.uniform(behavior.min_required_kwh, behavior.max_required_kwh)
            required = min(requested, max_feasible)
            sessions.append(EVConfig(
                asset_id=f"ev-{day.isoformat()}-{index + 1}",
                window=TimeWindow(arrival, departure),
                required_energy_kwh=required,
                max_power_kw=behavior.charger_power_kw,
                charger_efficiency=behavior.charger_efficiency,
            ))
    return tuple(sessions)


def generate_truth(config: GenerationConfig) -> GeneratedTruth:
    """Generate 15-minute exogenous truth; scheduling remains a later phase."""
    stream_names = ("weather", "load", "EV", "pump", "HVAC", "meter_noise", "missingness")
    seeds = {name: named_seed(config.root_seed, name) for name in stream_names}
    weather_rng = random.Random(seeds["weather"])
    load_rng = random.Random(seeds["load"])
    ev_rng = random.Random(seeds["EV"])
    intervals = make_intervals(config.start_utc, config.interval_count, 15)
    site = replace(config.site, evs=_make_ev_sessions(config, ev_rng, intervals[-1].end))
    cloud_center, cloud_jitter = {
        "clear": (0.92, 0.04),
        "cloudy": (0.62, 0.14),
        "monsoon_like": (0.38, 0.20),
    }[config.weather_scenario]
    solar_factor = {"standard": 1.0, "low": 0.75, "high": 1.15}[config.solar_scenario]
    cloud = cloud_center
    disturbances: list[TruthDisturbance] = []
    for interval in intervals:
        local = utc_to_local(interval.start + timedelta(minutes=7, seconds=30), site.timezone)
        hour = local.hour + local.minute / 60 + local.second / 3600
        weekday = local.weekday() < 5
        cloud = min(1.0, max(0.08, 0.75 * cloud + 0.25 * cloud_center + weather_rng.gauss(0, cloud_jitter)))
        solar_shape = math.sin(math.pi * (hour - 6.0) / 12.0) if 6.0 < hour < 18.0 else 0.0
        seasonal = 0.90 + 0.10 * math.cos(2 * math.pi * (local.timetuple().tm_yday - 172) / 365.0)
        pv_kw = min(site.pv.ac_capacity_kw, max(0.0, site.pv.ac_capacity_kw * solar_shape * cloud * seasonal * solar_factor))
        temperature_c = 27.0 + 5.0 * math.sin(math.pi * (hour - 7.0) / 12.0) + weather_rng.gauss(0, 0.4)
        load_factor = 0.65 if config.load_scenario == "low_activity" else 1.0
        cooling_factor = 1.5 if config.load_scenario == "high_cooling" else 1.0
        day_activity = config.day_activity_kw * load_factor * (1.0 if weekday else 0.45) if 8 <= hour < 18 else 0.0
        evening_activity = config.evening_activity_kw * load_factor if 18 <= hour < 22 else 0.0
        cooling = config.cooling_kw_per_c_above_28 * cooling_factor * max(0.0, temperature_c - 28.0)
        critical = max(0.0, config.critical_base_kw * (1.0 + load_rng.gauss(0, 0.01)))
        fixed = max(0.0, config.fixed_base_kw + day_activity + evening_activity + cooling + load_rng.gauss(0, 1.5))
        disturbances.append(TruthDisturbance(
            interval=interval,
            pv_available_kw=pv_kw,
            critical_load_kw=critical,
            fixed_load_kw=fixed,
            outdoor_temperature_c=temperature_c,
            tariff_inr_per_kwh=config.synthetic_tariff_inr_per_kwh,
        ))
    truth = tuple(disturbances)
    config_hash = canonical_sha256(config)
    truth_hash = canonical_sha256({"site": site, "disturbances": truth})
    manifest = TruthManifest(
        dataset_id=config.dataset_id,
        generator_version=GENERATOR_VERSION,
        canonical_model_version=CANONICAL_MODEL_VERSION,
        config_sha256=config_hash,
        truth_sha256=truth_hash,
        root_seed=config.root_seed,
        stream_seeds=tuple(sorted(seeds.items())),
        python_version=platform.python_version(),
        interval_minutes=15,
        site_timezone=site.timezone,
        start_utc=intervals[0].start,
        interval_count=len(intervals),
    )
    return GeneratedTruth(site, truth, manifest)
