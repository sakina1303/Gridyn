"""Canonical nonnegative AC-bus flows and power balance."""

from __future__ import annotations

from dataclasses import dataclass, fields

from .assets import GridConfig, PVConfig
from .units import balance_tolerance_kw, nonnegative


class PhysicalInfeasibility(ValueError):
    """A candidate physical schedule cannot be supplied without breaking a hard limit."""


@dataclass(frozen=True, slots=True)
class PhysicalFlows:
    pv_available_kw: float
    pv_curtailment_kw: float
    grid_import_kw: float
    grid_export_kw: float
    battery_charge_kw: float
    battery_discharge_kw: float
    critical_load_kw: float
    fixed_load_kw: float
    flexible_load_kw: float

    def __post_init__(self) -> None:
        for item in fields(self):
            nonnegative(getattr(self, item.name), item.name)
        if self.pv_curtailment_kw > self.pv_available_kw:
            raise ValueError("PV curtailment exceeds available PV")
        if self.grid_import_kw > 0 and self.grid_export_kw > 0:
            raise ValueError("simultaneous grid import and export")
        if self.battery_charge_kw > 0 and self.battery_discharge_kw > 0:
            raise ValueError("simultaneous battery charge and discharge")

    @property
    def net_grid_kw(self) -> float:
        return self.grid_import_kw - self.grid_export_kw

    @property
    def pv_used_kw(self) -> float:
        return self.pv_available_kw - self.pv_curtailment_kw

    @property
    def balance_residual_kw(self) -> float:
        supply = self.pv_used_kw + self.grid_import_kw + self.battery_discharge_kw
        demand = self.critical_load_kw + self.fixed_load_kw + self.flexible_load_kw + self.battery_charge_kw + self.grid_export_kw
        return supply - demand


def settle_flows(
    *,
    pv_available_kw: float,
    critical_load_kw: float,
    fixed_load_kw: float,
    flexible_load_kw: float,
    battery_charge_kw: float,
    battery_discharge_kw: float,
    grid: GridConfig,
    pv: PVConfig,
) -> PhysicalFlows:
    values = {
        "pv_available_kw": pv_available_kw,
        "critical_load_kw": critical_load_kw,
        "fixed_load_kw": fixed_load_kw,
        "flexible_load_kw": flexible_load_kw,
        "battery_charge_kw": battery_charge_kw,
        "battery_discharge_kw": battery_discharge_kw,
    }
    for name, value in values.items():
        nonnegative(value, name)
    if pv_available_kw > pv.ac_capacity_kw:
        raise PhysicalInfeasibility("available PV exceeds configured AC capacity")
    if battery_charge_kw > 0 and battery_discharge_kw > 0:
        raise PhysicalInfeasibility("simultaneous battery charge and discharge")

    net_demand = critical_load_kw + fixed_load_kw + flexible_load_kw + battery_charge_kw - pv_available_kw - battery_discharge_kw
    tolerance = balance_tolerance_kw(max(grid.import_limit_kw, grid.export_limit_kw, pv.ac_capacity_kw))
    if net_demand > grid.import_limit_kw + tolerance:
        raise PhysicalInfeasibility("grid import limit cannot serve scheduled load, including critical demand")

    if net_demand >= 0:
        grid_import = min(net_demand, grid.import_limit_kw)
        grid_export = 0.0
        curtailment = 0.0
    else:
        grid_import = 0.0
        grid_export = min(-net_demand, grid.export_limit_kw)
        curtailment = -net_demand - grid_export
        if curtailment > pv_available_kw:
            raise PhysicalInfeasibility("battery surplus cannot be curtailed as PV")
        if curtailment > 0 and not pv.allow_curtailment:
            raise PhysicalInfeasibility("PV surplus cannot be exported or curtailed")

    flows = PhysicalFlows(
        pv_available_kw=pv_available_kw,
        pv_curtailment_kw=max(0.0, curtailment),
        grid_import_kw=max(0.0, grid_import),
        grid_export_kw=max(0.0, grid_export),
        battery_charge_kw=battery_charge_kw,
        battery_discharge_kw=battery_discharge_kw,
        critical_load_kw=critical_load_kw,
        fixed_load_kw=fixed_load_kw,
        flexible_load_kw=flexible_load_kw,
    )
    if abs(flows.balance_residual_kw) > tolerance:
        raise PhysicalInfeasibility("power balance residual exceeds canonical tolerance")
    return flows
