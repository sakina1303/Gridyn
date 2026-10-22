"""Single authority for power, energy, duration, and numerical tolerance."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite


SUPPORTED_INTERVAL_MINUTES = (15, 30, 60)


def finite_number(value: float, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value):
        raise ValueError(f"{name} must be a finite number")
    return float(value)


def nonnegative(value: float, name: str) -> float:
    result = finite_number(value, name)
    if result < 0:
        raise ValueError(f"{name} must be nonnegative")
    return result


@dataclass(frozen=True, slots=True)
class PowerKW:
    value: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", finite_number(self.value, "power kW"))


@dataclass(frozen=True, slots=True)
class EnergyKWh:
    value: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", finite_number(self.value, "energy kWh"))


@dataclass(frozen=True, slots=True)
class IntervalDuration:
    minutes: int

    def __post_init__(self) -> None:
        if isinstance(self.minutes, bool) or self.minutes not in SUPPORTED_INTERVAL_MINUTES:
            raise ValueError(f"interval minutes must be one of {SUPPORTED_INTERVAL_MINUTES}")

    @property
    def hours(self) -> float:
        return self.minutes / 60.0


def energy_from_power(power: PowerKW, duration: IntervalDuration) -> EnergyKWh:
    return EnergyKWh(power.value * duration.hours)


def average_power_from_energy(energy: EnergyKWh, duration: IntervalDuration) -> PowerKW:
    return PowerKW(energy.value / duration.hours)


def parse_power(value: float, unit: str) -> PowerKW:
    factors = {"W": 0.001, "kW": 1.0, "MW": 1000.0}
    if unit not in factors:
        raise ValueError(f"unsupported power unit: {unit}")
    return PowerKW(finite_number(value, "power") * factors[unit])


def parse_energy(value: float, unit: str) -> EnergyKWh:
    factors = {"Wh": 0.001, "kWh": 1.0, "MWh": 1000.0}
    if unit not in factors:
        raise ValueError(f"unsupported energy unit: {unit}")
    return EnergyKWh(finite_number(value, "energy") * factors[unit])


def balance_tolerance_kw(site_rating_kw: float) -> float:
    return max(1e-6, 1e-7 * nonnegative(site_rating_kw, "site rating kW"))
