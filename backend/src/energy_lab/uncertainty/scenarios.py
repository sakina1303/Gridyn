"""Immutable synthetic stress overrides; each retains its own provenance."""

from __future__ import annotations

from dataclasses import dataclass, replace

from energy_lab.core.assets import SiteConfig
from energy_lab.core.units import finite_number, nonnegative
from energy_lab.simulation.engine import TruthDisturbance


@dataclass(frozen=True, slots=True)
class StressSpec:
    scenario_id: str
    pv_factor: float = 1.0
    critical_load_factor: float = 1.0
    fixed_load_factor: float = 1.0
    initial_battery_energy_kwh: float | None = None
    ev_required_factor: float = 1.0
    provenance: str = "declared_synthetic_stress"

    def __post_init__(self) -> None:
        if not self.scenario_id:
            raise ValueError("stress scenario id is required")
        for name in ("pv_factor", "critical_load_factor", "fixed_load_factor", "ev_required_factor"):
            nonnegative(getattr(self, name), name)
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
    evs = tuple(replace(ev, required_energy_kwh=ev.required_energy_kwh * spec.ev_required_factor)
                for ev in site.evs)
    stressed_site = replace(site, battery=battery, evs=evs)
    stressed_truth = tuple(replace(
        item,
        pv_available_kw=min(site.pv.ac_capacity_kw, item.pv_available_kw * spec.pv_factor),
        critical_load_kw=item.critical_load_kw * spec.critical_load_factor,
        fixed_load_kw=item.fixed_load_kw * spec.fixed_load_factor,
    ) for item in truth)
    return stressed_site, stressed_truth
