"""Deterministic battery state transition at the AC bus."""

from __future__ import annotations

from dataclasses import dataclass

from energy_lab.core.assets import BatteryConfig
from energy_lab.core.units import IntervalDuration, PowerKW, energy_from_power, nonnegative


@dataclass(frozen=True, slots=True)
class BatteryState:
    energy_kwh: float
    previous_net_discharge_kw: float = 0.0


def transition_battery(
    config: BatteryConfig | None,
    state: BatteryState | None,
    *,
    charge_kw: float,
    discharge_kw: float,
    duration: IntervalDuration,
) -> BatteryState | None:
    nonnegative(charge_kw, "battery charge kW")
    nonnegative(discharge_kw, "battery discharge kW")
    if config is None:
        if charge_kw != 0 or discharge_kw != 0:
            raise ValueError("battery power scheduled without a battery")
        return None
    if state is None:
        raise ValueError("battery state is required")
    if charge_kw > 0 and discharge_kw > 0:
        raise ValueError("simultaneous battery charge and discharge")
    if charge_kw > config.max_charge_kw or discharge_kw > config.max_discharge_kw:
        raise ValueError("battery power rating exceeded")
    net_discharge_kw = discharge_kw - charge_kw
    if config.max_ramp_kw_per_hour is not None:
        if abs(net_discharge_kw - state.previous_net_discharge_kw) > config.max_ramp_kw_per_hour * duration.hours + 1e-9:
            raise ValueError("battery ramp limit exceeded")

    charge_energy = energy_from_power(PowerKW(charge_kw), duration).value
    discharge_energy = energy_from_power(PowerKW(discharge_kw), duration).value
    next_energy = state.energy_kwh + config.charge_efficiency * charge_energy - discharge_energy / config.discharge_efficiency
    if next_energy < config.min_energy_kwh or next_energy > config.max_energy_kwh:
        raise ValueError("battery SOC limit exceeded")
    return BatteryState(next_energy, net_discharge_kw)
