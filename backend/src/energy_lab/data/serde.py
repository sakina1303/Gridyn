"""Explicit JSON serialization for persisted canonical research objects."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime

from energy_lab.core.assets import BatteryConfig, EVConfig, GridConfig, HVACConfig, PVConfig, PumpConfig, SiteConfig
from energy_lab.core.time import TimeInterval, TimeWindow
from energy_lab.simulation.engine import CandidateScheduleStep, TruthDisturbance
from energy_lab.simulation.observer import ObservedRecord


def _time(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _window(raw: dict) -> TimeWindow:
    return TimeWindow(_time(raw["start"]), _time(raw["end"]))


def site_to_dict(site: SiteConfig) -> dict:
    def render(value):
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, tuple):
            return [render(item) for item in value]
        if isinstance(value, dict):
            return {key: render(item) for key, item in value.items()}
        return value
    return render(asdict(site))


def site_from_dict(raw: dict) -> SiteConfig:
    return SiteConfig(
        raw["site_id"], raw["timezone"], GridConfig(**raw["grid"]), PVConfig(**raw["pv"]),
        BatteryConfig(**raw["battery"]) if raw.get("battery") else None,
        evs=tuple(EVConfig(asset_id=item["asset_id"], window=_window(item["window"]),
                           required_energy_kwh=item["required_energy_kwh"], max_power_kw=item["max_power_kw"],
                           charger_efficiency=item.get("charger_efficiency", 1.0),
                           max_ramp_kw_per_hour=item.get("max_ramp_kw_per_hour")) for item in raw.get("evs", [])),
        pumps=tuple(PumpConfig(asset_id=item["asset_id"], window=_window(item["window"]),
                               rated_power_kw=item["rated_power_kw"], required_runtime_hours=item["required_runtime_hours"],
                               minimum_run_intervals=item.get("minimum_run_intervals", 1)) for item in raw.get("pumps", [])),
        hvacs=tuple(HVACConfig(asset_id=item["asset_id"], windows=tuple(_window(window) for window in item["windows"]),
                               min_power_kw=item["min_power_kw"], max_power_kw=item["max_power_kw"],
                               max_ramp_kw_per_hour=item.get("max_ramp_kw_per_hour")) for item in raw.get("hvacs", [])),
    )


def truth_to_dict(item: TruthDisturbance) -> dict:
    return {"start": item.interval.start.isoformat(), "end": item.interval.end.isoformat(),
            "pv_available_kw": item.pv_available_kw, "critical_load_kw": item.critical_load_kw,
            "fixed_load_kw": item.fixed_load_kw, "outdoor_temperature_c": item.outdoor_temperature_c,
            "tariff_inr_per_kwh": item.tariff_inr_per_kwh}


def truth_from_dict(raw: dict) -> TruthDisturbance:
    return TruthDisturbance(TimeInterval(_time(raw["start"]), _time(raw["end"])),
                            raw["pv_available_kw"], raw["critical_load_kw"], raw["fixed_load_kw"],
                            raw.get("outdoor_temperature_c"), raw.get("tariff_inr_per_kwh"))


def record_to_dict(item: ObservedRecord) -> dict:
    return {"start": item.interval.start.isoformat(), "end": item.interval.end.isoformat(),
            "quantity": item.quantity, "value": item.value, "unit": item.unit}


def record_from_dict(raw: dict) -> ObservedRecord:
    return ObservedRecord(TimeInterval(_time(raw["start"]), _time(raw["end"])),
                          raw["quantity"], raw["value"], raw["unit"])


def schedule_to_dict(item: CandidateScheduleStep) -> dict:
    return {"start": item.interval.start.isoformat(), "end": item.interval.end.isoformat(),
            "battery_charge_kw": item.battery_charge_kw, "battery_discharge_kw": item.battery_discharge_kw,
            "ev_power_kw": dict(item.ev_power_kw), "pump_on": dict(item.pump_on),
            "hvac_power_kw": dict(item.hvac_power_kw)}


def schedule_from_dict(raw: dict) -> CandidateScheduleStep:
    return CandidateScheduleStep(TimeInterval(_time(raw["start"]), _time(raw["end"])),
                                 raw.get("battery_charge_kw", 0), raw.get("battery_discharge_kw", 0),
                                 raw.get("ev_power_kw", {}), raw.get("pump_on", {}), raw.get("hvac_power_kw", {}))
