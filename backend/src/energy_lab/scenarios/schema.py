"""Scenario overrides that preserve paired exogenous truth."""

from __future__ import annotations

from dataclasses import dataclass, replace

from energy_lab.core.assets import SiteConfig
from energy_lab.core.units import nonnegative


@dataclass(frozen=True, slots=True)
class ScenarioConfig:
    scenario_id: str
    dataset_id: str
    grid_import_limit_kw: float | None = None
    grid_export_limit_kw: float | None = None
    battery_max_charge_kw: float | None = None
    battery_max_discharge_kw: float | None = None
    seed: int = 7

    def __post_init__(self) -> None:
        if not self.scenario_id or not self.dataset_id:
            raise ValueError("scenario and dataset IDs are required")
        for name in ("grid_import_limit_kw", "grid_export_limit_kw",
                     "battery_max_charge_kw", "battery_max_discharge_kw"):
            value = getattr(self, name)
            if value is not None:
                nonnegative(value, name)


def apply_scenario(site: SiteConfig, config: ScenarioConfig) -> SiteConfig:
    grid = replace(site.grid,
        import_limit_kw=site.grid.import_limit_kw if config.grid_import_limit_kw is None else config.grid_import_limit_kw,
        export_limit_kw=site.grid.export_limit_kw if config.grid_export_limit_kw is None else config.grid_export_limit_kw)
    battery = site.battery
    if config.battery_max_charge_kw is not None or config.battery_max_discharge_kw is not None:
        if battery is None:
            raise ValueError("battery override requires a configured battery")
        battery = replace(battery,
            max_charge_kw=battery.max_charge_kw if config.battery_max_charge_kw is None else config.battery_max_charge_kw,
            max_discharge_kw=battery.max_discharge_kw if config.battery_max_discharge_kw is None else config.battery_max_discharge_kw)
    return replace(site, grid=grid, battery=battery)
