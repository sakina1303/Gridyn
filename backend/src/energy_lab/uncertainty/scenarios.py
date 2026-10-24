"""Immutable synthetic stress overrides; each retains its own provenance."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import timedelta

from energy_lab.core.assets import SiteConfig
from energy_lab.core.time import TimeWindow
from energy_lab.core.units import finite_number, nonnegative
from energy_lab.simulation.engine import TruthDisturbance


@dataclass(frozen=True, slots=True)
class StressSpec:
    scenario_id: str
    pv_factor: float = 1.0
    critical_load_factor: float = 1.0
    fixed_load_factor: float = 1.0
    initial_battery_energy_kwh: float | None = None
    battery_charge_factor: float = 1.0
    battery_discharge_factor: float = 1.0
    ev_required_factor: float = 1.0
    ev_arrival_shift_intervals: int = 0
    ev_departure_shift_intervals: int = 0
    pump_runtime_factor: float = 1.0
    outdoor_temperature_delta_c: float = 0.0
    provenance: str = "declared_synthetic_stress"

    def __post_init__(self) -> None:
        if not self.scenario_id:
            raise ValueError("stress scenario id is required")
        for name in ("pv_factor", "critical_load_factor", "fixed_load_factor", "ev_required_factor",
                     "battery_charge_factor", "battery_discharge_factor", "pump_runtime_factor"):
            nonnegative(getattr(self, name), name)
        for name in ("ev_arrival_shift_intervals", "ev_departure_shift_intervals"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int):
                raise ValueError(f"{name} must be an integer")
        finite_number(self.outdoor_temperature_delta_c, "outdoor temperature shift C")
        if self.battery_charge_factor > 1 or self.battery_discharge_factor > 1:
            raise ValueError("battery stress factors cannot exceed configured ratings")
        if self.initial_battery_energy_kwh is not None:
            finite_number(self.initial_battery_energy_kwh, "stressed initial battery energy")
        if self.provenance not in {"declared_synthetic_stress", "sampled_holdout"}:
            raise ValueError("unsupported stress provenance")


def apply_stress(
    site: SiteConfig, truth: tuple[TruthDisturbance, ...], spec: StressSpec,
) -> tuple[SiteConfig, tuple[TruthDisturbance, ...]]:
    battery = site.battery
    if spec.initial_battery_energy_kwh is not None:
        if battery is None:
            raise ValueError("initial SOC stress requires a configured battery")
        battery = replace(battery, initial_energy_kwh=spec.initial_battery_energy_kwh)
    if spec.battery_charge_factor != 1 or spec.battery_discharge_factor != 1:
        if battery is None:
            raise ValueError("battery rating stress requires a configured battery")
        battery = replace(battery,
                          max_charge_kw=battery.max_charge_kw * spec.battery_charge_factor,
                          max_discharge_kw=battery.max_discharge_kw * spec.battery_discharge_factor)
    evs = tuple(replace(ev,
        required_energy_kwh=ev.required_energy_kwh * spec.ev_required_factor,
        window=TimeWindow(ev.window.start + timedelta(minutes=15 * spec.ev_arrival_shift_intervals),
                          ev.window.end + timedelta(minutes=15 * spec.ev_departure_shift_intervals)))
        for ev in site.evs)
    pumps = tuple(replace(pump, required_runtime_hours=pump.required_runtime_hours * spec.pump_runtime_factor)
                  for pump in site.pumps)
    stressed_site = replace(site, battery=battery, evs=evs, pumps=pumps)
    stressed_truth = tuple(replace(
        item,
        pv_available_kw=min(site.pv.ac_capacity_kw, item.pv_available_kw * spec.pv_factor),
        critical_load_kw=item.critical_load_kw * spec.critical_load_factor,
        fixed_load_kw=item.fixed_load_kw * spec.fixed_load_factor,
        outdoor_temperature_c=(item.outdoor_temperature_c + spec.outdoor_temperature_delta_c
                               if item.outdoor_temperature_c is not None else None),
    ) for item in truth)
    return stressed_site, stressed_truth
