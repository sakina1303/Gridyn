"""EV, pump and conservative HVAC service tracking for a supplied schedule."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from energy_lab.core.assets import SiteConfig
from energy_lab.core.time import TimeInterval
from energy_lab.core.units import PowerKW, energy_from_power, nonnegative


@dataclass(frozen=True, slots=True)
class ServiceSnapshot:
    flexible_load_kw: float
    ev_delivered_kwh: tuple[tuple[str, float], ...]
    pump_runtime_hours: tuple[tuple[str, float], ...]
    hvac_power_kw: tuple[tuple[str, float], ...]


class LoadTracker:
    def __init__(self, site: SiteConfig) -> None:
        self.site = site
        self.ev_delivered = {ev.asset_id: 0.0 for ev in site.evs}
        self.ev_previous = {ev.asset_id: 0.0 for ev in site.evs}
        self.pump_runtime = {pump.asset_id: 0.0 for pump in site.pumps}
        self.pump_previous_on = {pump.asset_id: False for pump in site.pumps}
        self.pump_streak = {pump.asset_id: 0 for pump in site.pumps}
        self.hvac_previous = {hvac.asset_id: 0.0 for hvac in site.hvacs}

    def apply(
        self,
        interval: TimeInterval,
        *,
        ev_power_kw: Mapping[str, float],
        pump_on: Mapping[str, bool],
        hvac_power_kw: Mapping[str, float],
    ) -> ServiceSnapshot:
        ev_ids = set(self.ev_delivered)
        pump_ids = set(self.pump_runtime)
        hvac_ids = set(self.hvac_previous)
        if set(ev_power_kw) - ev_ids or set(pump_on) - pump_ids or set(hvac_power_kw) - hvac_ids:
            raise ValueError("schedule contains an unknown flexible asset")
        total_kw = 0.0
        duration = interval.duration

        for ev in self.site.evs:
            power = nonnegative(ev_power_kw.get(ev.asset_id, 0.0), f"EV {ev.asset_id} power")
            if power > ev.max_power_kw:
                raise ValueError(f"EV {ev.asset_id} power rating exceeded")
            if power > 0 and not ev.window.contains(interval):
                raise ValueError(f"EV {ev.asset_id} outside availability window")
            if ev.max_ramp_kw_per_hour is not None:
                if abs(power - self.ev_previous[ev.asset_id]) > ev.max_ramp_kw_per_hour * duration.hours + 1e-9:
                    raise ValueError(f"EV {ev.asset_id} ramp limit exceeded")
            self.ev_delivered[ev.asset_id] += energy_from_power(PowerKW(power), duration).value * ev.charger_efficiency
            self.ev_previous[ev.asset_id] = power
            total_kw += power
            if interval.end >= ev.window.end and self.ev_delivered[ev.asset_id] + 1e-6 < ev.required_energy_kwh:
                raise ValueError(f"EV {ev.asset_id} departure energy unmet")

        for pump in self.site.pumps:
            on = pump_on.get(pump.asset_id, False)
            if not isinstance(on, bool):
                raise ValueError(f"pump {pump.asset_id} schedule must be boolean")
            if on and not pump.window.contains(interval):
                raise ValueError(f"pump {pump.asset_id} outside availability window")
            was_on = self.pump_previous_on[pump.asset_id]
            streak = self.pump_streak[pump.asset_id]
            if was_on and not on and streak < pump.minimum_run_intervals:
                raise ValueError(f"pump {pump.asset_id} minimum run time violated")
            self.pump_streak[pump.asset_id] = (streak + 1 if was_on else 1) if on else 0
            self.pump_previous_on[pump.asset_id] = on
            if on:
                self.pump_runtime[pump.asset_id] += duration.hours
                total_kw += pump.rated_power_kw
            if interval.end >= pump.window.end and self.pump_runtime[pump.asset_id] + 1e-9 < pump.required_runtime_hours:
                raise ValueError(f"pump {pump.asset_id} required runtime unmet")

        hvac_actual: list[tuple[str, float]] = []
        for hvac in self.site.hvacs:
            power = nonnegative(hvac_power_kw.get(hvac.asset_id, 0.0), f"HVAC {hvac.asset_id} power")
            active = any(window.contains(interval) for window in hvac.windows)
            if active:
                if power < hvac.min_power_kw or power > hvac.max_power_kw:
                    raise ValueError(f"HVAC {hvac.asset_id} conservative power bound violated")
            elif power != 0:
                raise ValueError(f"HVAC {hvac.asset_id} outside approved window")
            if hvac.max_ramp_kw_per_hour is not None:
                if abs(power - self.hvac_previous[hvac.asset_id]) > hvac.max_ramp_kw_per_hour * duration.hours + 1e-9:
                    raise ValueError(f"HVAC {hvac.asset_id} ramp limit exceeded")
            self.hvac_previous[hvac.asset_id] = power
            total_kw += power
            hvac_actual.append((hvac.asset_id, power))

        return ServiceSnapshot(
            flexible_load_kw=total_kw,
            ev_delivered_kwh=tuple(sorted(self.ev_delivered.items())),
            pump_runtime_hours=tuple(sorted(self.pump_runtime.items())),
            hvac_power_kw=tuple(sorted(hvac_actual)),
        )

    def validate_complete(self) -> None:
        for ev in self.site.evs:
            if self.ev_delivered[ev.asset_id] + 1e-6 < ev.required_energy_kwh:
                raise ValueError(f"EV {ev.asset_id} departure energy unmet")
        for pump in self.site.pumps:
            if self.pump_runtime[pump.asset_id] + 1e-9 < pump.required_runtime_hours:
                raise ValueError(f"pump {pump.asset_id} required runtime unmet")
            if self.pump_previous_on[pump.asset_id] and self.pump_streak[pump.asset_id] < pump.minimum_run_intervals:
                raise ValueError(f"pump {pump.asset_id} minimum run time violated at horizon end")
