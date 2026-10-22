"""Derive analyst-visible observations from hidden synthetic truth.

Corruption details are returned separately for experiment scoring and must not be
passed to a readiness/forecasting model as if they were observed features.
"""

from __future__ import annotations

import platform
import random
from dataclasses import dataclass
from datetime import timedelta

from energy_lab.core.time import TimeInterval
from energy_lab.core.units import EnergyKWh, IntervalDuration, PowerKW, average_power_from_energy, energy_from_power, finite_number
from energy_lab.data.manifest import canonical_sha256, named_seed

from .generator import GeneratedTruth


POWER_QUANTITIES = ("pv_available_kw", "critical_load_kw", "fixed_load_kw")
TEMPERATURE_QUANTITY = "outdoor_temperature_c"
ALL_QUANTITIES = POWER_QUANTITIES + (TEMPERATURE_QUANTITY,)
OBSERVER_VERSION = "0.1.0"


@dataclass(frozen=True, slots=True)
class ObservationConfig:
    dataset_id: str
    root_seed: int
    interval_minutes: int = 15
    visible_quantities: tuple[str, ...] = ALL_QUANTITIES
    missing_probability: float = 0.0
    missing_blocks: tuple[tuple[int, int], ...] = ()  # start index, count on observed grid
    power_noise_std_kw: float = 0.0
    temperature_noise_std_c: float = 0.0
    power_bias_fraction: float = 0.0
    outlier_probability: float = 0.0
    outlier_multiplier: float = 2.0
    timestamp_shift_minutes: int = 0
    duplicate_indices: tuple[int, ...] = ()

    def __post_init__(self) -> None:
        if not self.dataset_id:
            raise ValueError("observation dataset_id is required")
        named_seed(self.root_seed, "validation")
        IntervalDuration(self.interval_minutes)
        if len(set(self.visible_quantities)) != len(self.visible_quantities):
            raise ValueError("visible quantities must be unique")
        if set(self.visible_quantities) - set(ALL_QUANTITIES):
            raise ValueError("unsupported visible quantity")
        for name in ("missing_probability", "outlier_probability"):
            value = finite_number(getattr(self, name), name)
            if not 0 <= value <= 1:
                raise ValueError(f"{name} must be in [0,1]")
        for name in ("power_noise_std_kw", "temperature_noise_std_c"):
            if finite_number(getattr(self, name), name) < 0:
                raise ValueError(f"{name} must be nonnegative")
        finite_number(self.power_bias_fraction, "power bias fraction")
        if finite_number(self.outlier_multiplier, "outlier multiplier") <= 0:
            raise ValueError("outlier multiplier must be positive")
        if isinstance(self.timestamp_shift_minutes, bool) or not isinstance(self.timestamp_shift_minutes, int):
            raise ValueError("timestamp shift must be an integer number of minutes")
        for start, count in self.missing_blocks:
            if not isinstance(start, int) or not isinstance(count, int) or start < 0 or count < 1:
                raise ValueError("missing blocks require nonnegative start and positive count")
        if any(isinstance(i, bool) or not isinstance(i, int) or i < 0 for i in self.duplicate_indices):
            raise ValueError("duplicate indices must be nonnegative integers")


@dataclass(frozen=True, slots=True)
class ObservedRecord:
    interval: TimeInterval
    quantity: str
    value: float
    unit: str

    def __post_init__(self) -> None:
        finite_number(self.value, "observed value")


@dataclass(frozen=True, slots=True)
class ObservationManifest:
    dataset_id: str
    truth_dataset_id: str
    truth_sha256: str
    observer_version: str
    config_sha256: str
    observed_sha256: str
    root_seed: int
    stream_seeds: tuple[tuple[str, int], ...]
    python_version: str
    interval_minutes: int
    site_timezone: str
    synthetic: bool = True


@dataclass(frozen=True, slots=True)
class ObservedDataset:
    records: tuple[ObservedRecord, ...]
    manifest: ObservationManifest


@dataclass(frozen=True, slots=True)
class HiddenCorruption:
    missing: tuple[tuple[str, int], ...]
    outliers: tuple[tuple[str, int], ...]
    duplicates: tuple[tuple[str, int], ...]
    timestamp_shift_minutes: int


@dataclass(frozen=True, slots=True)
class ObservationResult:
    observed: ObservedDataset
    hidden_corruption: HiddenCorruption


def _aggregate_truth(truth: GeneratedTruth, factor: int, quantity: str, group_index: int) -> tuple[TimeInterval, float]:
    group = truth.disturbances[group_index * factor:(group_index + 1) * factor]
    interval = TimeInterval(group[0].interval.start, group[-1].interval.end)
    if quantity == TEMPERATURE_QUANTITY:
        values = [item.outdoor_temperature_c for item in group]
        if any(value is None for value in values):
            raise ValueError("temperature observation requested but truth has no temperature")
        return interval, sum(values) / len(values)
    energy = sum(energy_from_power(PowerKW(getattr(item, quantity)), item.interval.duration).value for item in group)
    return interval, average_power_from_energy(EnergyKWh(energy), interval.duration).value


def observe_truth(truth: GeneratedTruth, config: ObservationConfig) -> ObservationResult:
    if config.dataset_id == truth.manifest.dataset_id:
        raise ValueError("truth and observation dataset IDs must differ")
    factor = config.interval_minutes // 15
    if config.interval_minutes % 15 or len(truth.disturbances) % factor:
        raise ValueError("observation resolution must divide complete truth horizon")
    group_count = len(truth.disturbances) // factor
    if any(start + count > group_count for start, count in config.missing_blocks):
        raise ValueError("missing block exceeds observation horizon")
    if any(index >= group_count for index in config.duplicate_indices):
        raise ValueError("duplicate index exceeds observation horizon")

    seeds = {name: named_seed(config.root_seed, name) for name in ("meter_noise", "missingness", "outliers")}
    noise_rng = random.Random(seeds["meter_noise"])
    missing_rng = random.Random(seeds["missingness"])
    outlier_rng = random.Random(seeds["outliers"])
    block_indices = {index for start, count in config.missing_blocks for index in range(start, start + count)}
    duplicate_indices = set(config.duplicate_indices)
    records: list[ObservedRecord] = []
    missing: list[tuple[str, int]] = []
    outliers: list[tuple[str, int]] = []
    duplicates: list[tuple[str, int]] = []
    for quantity in config.visible_quantities:
        unit = "°C" if quantity == TEMPERATURE_QUANTITY else "kW"
        for index in range(group_count):
            interval, value = _aggregate_truth(truth, factor, quantity, index)
            if index in block_indices or missing_rng.random() < config.missing_probability:
                missing.append((quantity, index))
                continue
            if quantity in POWER_QUANTITIES:
                value = value * (1.0 + config.power_bias_fraction) + noise_rng.gauss(0.0, config.power_noise_std_kw)
            else:
                value += noise_rng.gauss(0.0, config.temperature_noise_std_c)
            if outlier_rng.random() < config.outlier_probability:
                value *= config.outlier_multiplier
                outliers.append((quantity, index))
            shift = timedelta(minutes=config.timestamp_shift_minutes)
            observed_interval = TimeInterval(interval.start + shift, interval.end + shift)
            record = ObservedRecord(observed_interval, quantity, value, unit)
            records.append(record)
            if index in duplicate_indices:
                records.append(record)
                duplicates.append((quantity, index))
    records.sort(key=lambda item: (item.quantity, item.interval.start))
    observed_records = tuple(records)
    manifest = ObservationManifest(
        dataset_id=config.dataset_id,
        truth_dataset_id=truth.manifest.dataset_id,
        truth_sha256=truth.manifest.truth_sha256,
        observer_version=OBSERVER_VERSION,
        config_sha256=canonical_sha256(config),
        observed_sha256=canonical_sha256(observed_records),
        root_seed=config.root_seed,
        stream_seeds=tuple(sorted(seeds.items())),
        python_version=platform.python_version(),
        interval_minutes=config.interval_minutes,
        site_timezone=truth.site.timezone,
    )
    return ObservationResult(
        ObservedDataset(observed_records, manifest),
        HiddenCorruption(tuple(missing), tuple(outliers), tuple(duplicates), config.timestamp_shift_minutes),
    )
