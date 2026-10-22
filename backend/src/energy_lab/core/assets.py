"""Typed, immutable site and asset constraints using canonical units."""

from __future__ import annotations

from dataclasses import dataclass, field

from .time import TimeWindow, site_zone
from .units import finite_number, nonnegative


def _positive(value: float, name: str) -> float:
    result = nonnegative(value, name)
    if result <= 0:
        raise ValueError(f"{name} must be positive")
    return result


def _fraction(value: float, name: str, *, allow_zero: bool = False) -> float:
    result = finite_number(value, name)
    if not (0 <= result <= 1) or (not allow_zero and result == 0):
        raise ValueError(f"{name} must be {'between 0 and 1' if allow_zero else 'in (0, 1]'}")
    return result


@dataclass(frozen=True, slots=True)
class GridConfig:
    import_limit_kw: float
    export_limit_kw: float

    def __post_init__(self) -> None:
        nonnegative(self.import_limit_kw, "grid import limit kW")
        nonnegative(self.export_limit_kw, "grid export limit kW")


@dataclass(frozen=True, slots=True)
class PVConfig:
    ac_capacity_kw: float
    allow_curtailment: bool = True

    def __post_init__(self) -> None:
        nonnegative(self.ac_capacity_kw, "PV AC capacity kW")
        if not isinstance(self.allow_curtailment, bool):
            raise ValueError("allow_curtailment must be bool")


@dataclass(frozen=True, slots=True)
class BatteryConfig:
    nominal_capacity_kwh: float
    min_soc_fraction: float
    max_soc_fraction: float
    initial_energy_kwh: float
    max_charge_kw: float
    max_discharge_kw: float
    charge_efficiency: float
    discharge_efficiency: float
    min_terminal_energy_kwh: float | None = None
    max_ramp_kw_per_hour: float | None = None

    def __post_init__(self) -> None:
        _positive(self.nominal_capacity_kwh, "battery nominal capacity kWh")
        _fraction(self.min_soc_fraction, "minimum SOC fraction", allow_zero=True)
        _fraction(self.max_soc_fraction, "maximum SOC fraction")
        if self.min_soc_fraction >= self.max_soc_fraction:
            raise ValueError("minimum SOC must be below maximum SOC")
        nonnegative(self.max_charge_kw, "battery charge rating kW")
        nonnegative(self.max_discharge_kw, "battery discharge rating kW")
        _fraction(self.charge_efficiency, "charge efficiency")
        _fraction(self.discharge_efficiency, "discharge efficiency")
        if not self.min_energy_kwh <= self.initial_energy_kwh <= self.max_energy_kwh:
            raise ValueError("initial battery energy outside SOC limits")
        if self.min_terminal_energy_kwh is not None:
            if not self.min_energy_kwh <= self.min_terminal_energy_kwh <= self.max_energy_kwh:
                raise ValueError("terminal battery energy outside SOC limits")
            if self.min_terminal_energy_kwh < self.initial_energy_kwh:
                raise ValueError("terminal battery energy cannot be below initial energy without a carryover model")
        if self.max_ramp_kw_per_hour is not None:
            nonnegative(self.max_ramp_kw_per_hour, "battery ramp kW per hour")

    @property
    def min_energy_kwh(self) -> float:
        return self.nominal_capacity_kwh * self.min_soc_fraction

    @property
    def max_energy_kwh(self) -> float:
        return self.nominal_capacity_kwh * self.max_soc_fraction

    @property
    def terminal_requirement_kwh(self) -> float:
        return self.initial_energy_kwh if self.min_terminal_energy_kwh is None else self.min_terminal_energy_kwh


@dataclass(frozen=True, slots=True)
class EVConfig:
    asset_id: str
    window: TimeWindow
    required_energy_kwh: float
    max_power_kw: float
    charger_efficiency: float = 1.0
    max_ramp_kw_per_hour: float | None = None

    def __post_init__(self) -> None:
        if not self.asset_id:
            raise ValueError("EV asset_id is required")
        nonnegative(self.required_energy_kwh, "EV required energy kWh")
        _positive(self.max_power_kw, "EV max power kW")
        _fraction(self.charger_efficiency, "EV charger efficiency")
        if self.max_ramp_kw_per_hour is not None:
            nonnegative(self.max_ramp_kw_per_hour, "EV ramp kW per hour")


@dataclass(frozen=True, slots=True)
class PumpConfig:
    asset_id: str
    window: TimeWindow
    rated_power_kw: float
    required_runtime_hours: float
    minimum_run_intervals: int = 1

    def __post_init__(self) -> None:
        if not self.asset_id:
            raise ValueError("pump asset_id is required")
        _positive(self.rated_power_kw, "pump rated power kW")
        nonnegative(self.required_runtime_hours, "pump required runtime hours")
        if isinstance(self.minimum_run_intervals, bool) or not isinstance(self.minimum_run_intervals, int) or self.minimum_run_intervals < 1:
            raise ValueError("minimum_run_intervals must be a positive integer")


@dataclass(frozen=True, slots=True)
class HVACConfig:
    asset_id: str
    windows: tuple[TimeWindow, ...]
    min_power_kw: float
    max_power_kw: float
    max_ramp_kw_per_hour: float | None = None

    def __post_init__(self) -> None:
        if not self.asset_id:
            raise ValueError("HVAC asset_id is required")
        nonnegative(self.min_power_kw, "HVAC minimum power kW")
        nonnegative(self.max_power_kw, "HVAC maximum power kW")
        if self.min_power_kw > self.max_power_kw:
            raise ValueError("HVAC minimum power exceeds maximum")
        if not self.windows:
            raise ValueError("HVAC requires at least one approved window")
        ordered = sorted(self.windows, key=lambda w: w.start)
        if any(a.end > b.start for a, b in zip(ordered, ordered[1:])):
            raise ValueError("HVAC windows must not overlap")
        if self.max_ramp_kw_per_hour is not None:
            nonnegative(self.max_ramp_kw_per_hour, "HVAC ramp kW per hour")


@dataclass(frozen=True, slots=True)
class SiteConfig:
    site_id: str
    timezone: str
    grid: GridConfig
    pv: PVConfig
    battery: BatteryConfig | None = None
    evs: tuple[EVConfig, ...] = field(default_factory=tuple)
    pumps: tuple[PumpConfig, ...] = field(default_factory=tuple)
    hvacs: tuple[HVACConfig, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.site_id:
            raise ValueError("site_id is required")
        site_zone(self.timezone)
        ids = [a.asset_id for a in (*self.evs, *self.pumps, *self.hvacs)]
        if len(ids) != len(set(ids)):
            raise ValueError("asset IDs must be unique at a site")
