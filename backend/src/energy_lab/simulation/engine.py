"""Deterministic 15-minute replay of a supplied schedule against truth disturbances."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

from energy_lab.core.assets import SiteConfig
from energy_lab.core.flows import PhysicalFlows, PhysicalInfeasibility, settle_flows
from energy_lab.core.time import TimeInterval, validate_contiguous
from energy_lab.core.units import PowerKW, energy_from_power, finite_number, nonnegative

from .battery import BatteryState, transition_battery
from .loads import LoadTracker, ServiceSnapshot


class InfeasibleSchedule(ValueError):
    def __init__(self, reason: str, interval_index: int | None = None) -> None:
        self.reason = reason
        self.interval_index = interval_index
        label = f"interval {interval_index}: " if interval_index is not None else ""
        super().__init__(label + reason)


@dataclass(frozen=True, slots=True)
class TruthDisturbance:
    interval: TimeInterval
    pv_available_kw: float
    critical_load_kw: float
    fixed_load_kw: float
    outdoor_temperature_c: float | None = None
    tariff_inr_per_kwh: float | None = None

    def __post_init__(self) -> None:
        nonnegative(self.pv_available_kw, "available PV kW")
        nonnegative(self.critical_load_kw, "critical load kW")
        nonnegative(self.fixed_load_kw, "fixed load kW")
        if self.outdoor_temperature_c is not None:
            finite_number(self.outdoor_temperature_c, "outdoor temperature C")
        if self.tariff_inr_per_kwh is not None:
            finite_number(self.tariff_inr_per_kwh, "tariff INR/kWh")


@dataclass(frozen=True, slots=True)
class CandidateScheduleStep:
    interval: TimeInterval
    battery_charge_kw: float = 0.0
    battery_discharge_kw: float = 0.0
    ev_power_kw: Mapping[str, float] = field(default_factory=dict)
    pump_on: Mapping[str, bool] = field(default_factory=dict)
    hvac_power_kw: Mapping[str, float] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class TrajectoryStep:
    interval: TimeInterval
    flows: PhysicalFlows
    battery_energy_before_kwh: float | None
    battery_energy_after_kwh: float | None
    critical_served_kw: float
    services: ServiceSnapshot


@dataclass(frozen=True, slots=True)
class Trajectory:
    site_id: str
    seed: int
    steps: tuple[TrajectoryStep, ...]
    final_battery_energy_kwh: float | None

    @property
    def grid_import_kwh(self) -> float:
        return sum(energy_from_power(PowerKW(s.flows.grid_import_kw), s.interval.duration).value for s in self.steps)

    @property
    def grid_export_kwh(self) -> float:
        return sum(energy_from_power(PowerKW(s.flows.grid_export_kw), s.interval.duration).value for s in self.steps)

    @property
    def pv_curtailment_kwh(self) -> float:
        return sum(energy_from_power(PowerKW(s.flows.pv_curtailment_kw), s.interval.duration).value for s in self.steps)


def _validate_asset_windows(site: SiteConfig, intervals: tuple[TimeInterval, ...]) -> None:
    boundaries = {interval.start for interval in intervals} | {intervals[-1].end}
    horizon_start, horizon_end = intervals[0].start, intervals[-1].end
    windows = [asset.window for asset in (*site.evs, *site.pumps)]
    windows.extend(window for hvac in site.hvacs for window in hvac.windows)
    for window in windows:
        if window.start < horizon_start or window.end > horizon_end:
            raise ValueError("asset window must be inside simulation horizon")
        if window.start not in boundaries or window.end not in boundaries:
            raise ValueError("asset windows must align to interval boundaries")


def simulate(
    site: SiteConfig,
    truth: tuple[TruthDisturbance, ...],
    seed: int,
    schedule: tuple[CandidateScheduleStep, ...],
) -> Trajectory:
    """Replay, never choose, an action schedule on complete exogenous truth."""
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("seed must be an integer")
    if not truth or len(truth) != len(schedule):
        raise ValueError("truth and schedule must have equal nonzero length")
    intervals = tuple(item.interval for item in truth)
    validate_contiguous(intervals, required_minutes=15)
    _validate_asset_windows(site, intervals)
    if any(action.interval != interval for action, interval in zip(schedule, intervals)):
        raise ValueError("schedule intervals must match truth intervals")

    battery_state = BatteryState(site.battery.initial_energy_kwh) if site.battery else None
    loads = LoadTracker(site)
    steps: list[TrajectoryStep] = []
    for index, (disturbance, action) in enumerate(zip(truth, schedule)):
        try:
            before = battery_state.energy_kwh if battery_state else None
            next_battery = transition_battery(
                site.battery,
                battery_state,
                charge_kw=action.battery_charge_kw,
                discharge_kw=action.battery_discharge_kw,
                duration=disturbance.interval.duration,
            )
            service = loads.apply(
                disturbance.interval,
                ev_power_kw=action.ev_power_kw,
                pump_on=action.pump_on,
                hvac_power_kw=action.hvac_power_kw,
            )
            flows = settle_flows(
                pv_available_kw=disturbance.pv_available_kw,
                critical_load_kw=disturbance.critical_load_kw,
                fixed_load_kw=disturbance.fixed_load_kw,
                flexible_load_kw=service.flexible_load_kw,
                battery_charge_kw=action.battery_charge_kw,
                battery_discharge_kw=action.battery_discharge_kw,
                grid=site.grid,
                pv=site.pv,
            )
            battery_state = next_battery
            steps.append(TrajectoryStep(
                interval=disturbance.interval,
                flows=flows,
                battery_energy_before_kwh=before,
                battery_energy_after_kwh=battery_state.energy_kwh if battery_state else None,
                critical_served_kw=disturbance.critical_load_kw,
                services=service,
            ))
        except (ValueError, PhysicalInfeasibility) as exc:
            raise InfeasibleSchedule(str(exc), index) from exc

    try:
        loads.validate_complete()
        if site.battery and battery_state is not None:
            if battery_state.energy_kwh < site.battery.terminal_requirement_kwh:
                raise ValueError("terminal battery SOC requirement unmet")
    except ValueError as exc:
        raise InfeasibleSchedule(str(exc)) from exc

    return Trajectory(site.site_id, seed, tuple(steps), battery_state.energy_kwh if battery_state else None)
