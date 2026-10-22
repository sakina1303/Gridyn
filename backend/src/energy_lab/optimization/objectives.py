"""Named objective profiles; tariffs are caller supplied, never invented."""

from __future__ import annotations

from dataclasses import dataclass

import pyomo.environ as pyo

from energy_lab.core.units import finite_number, nonnegative
from energy_lab.simulation.engine import Trajectory, TruthDisturbance


@dataclass(frozen=True, slots=True)
class ObjectiveConfig:
    profile: str  # cost, peak, solar_use
    import_tariff_inr_per_kwh: tuple[float, ...] = ()
    export_credit_inr_per_kwh: tuple[float, ...] = ()
    demand_charge_inr_per_kw: float = 0.0
    curtailment_penalty_inr_per_kwh: float = 0.0
    battery_throughput_penalty_inr_per_kwh: float = 0.0

    def __post_init__(self) -> None:
        if self.profile not in {"cost", "peak", "solar_use"}:
            raise ValueError("unsupported objective profile")
        for series in (self.import_tariff_inr_per_kwh, self.export_credit_inr_per_kwh):
            for value in series:
                finite_number(value, "tariff/credit coefficient")
        for name in ("demand_charge_inr_per_kw", "curtailment_penalty_inr_per_kwh",
                     "battery_throughput_penalty_inr_per_kwh"):
            nonnegative(getattr(self, name), name)


def attach_objective(model, truth: tuple[TruthDisturbance, ...], config: ObjectiveConfig) -> None:
    n = len(truth)
    if config.profile == "cost" and (len(config.import_tariff_inr_per_kwh) != n or
                                      len(config.export_credit_inr_per_kwh) != n):
        raise ValueError("cost profile requires explicit import and export rates for every interval")
    model.peak_kw = pyo.Var(domain=pyo.NonNegativeReals)
    model.peak_link = pyo.ConstraintList()
    for t in range(n):
        model.peak_link.add(model.peak_kw >= model.import_kw[t])
    model.peak_kw.setub(max(0.0, max(item.critical_load_kw + item.fixed_load_kw for item in truth) +
                             max(pyo.value(model.import_kw[t].ub) for t in range(n))))
    energy_cost = sum(
        (model.import_kw[t] * config.import_tariff_inr_per_kwh[t] -
         model.export_kw[t] * config.export_credit_inr_per_kwh[t]) * 0.25
        for t in range(n)
    ) if config.profile == "cost" else 0
    curtailment = sum((truth[t].pv_available_kw - model.pv_used_kw[t]) * 0.25 for t in range(n))
    throughput = sum((model.charge_kw[t] + model.discharge_kw[t]) * 0.25 for t in range(n))
    if config.profile == "cost":
        expression = energy_cost + config.demand_charge_inr_per_kw * model.peak_kw + \
            config.curtailment_penalty_inr_per_kwh * curtailment + \
            config.battery_throughput_penalty_inr_per_kwh * throughput
    elif config.profile == "peak":
        expression = model.peak_kw + 1e-6 * curtailment
    else:
        expression = curtailment + 1e-6 * model.peak_kw
    model.objective = pyo.Objective(expr=expression, sense=pyo.minimize)


def recompute_objective(trajectory: Trajectory, truth: tuple[TruthDisturbance, ...], config: ObjectiveConfig) -> float:
    if len(trajectory.steps) != len(truth):
        raise ValueError("trajectory/truth length mismatch")
    imports = [step.flows.grid_import_kw for step in trajectory.steps]
    exports = [step.flows.grid_export_kw for step in trajectory.steps]
    curtailed = sum(step.flows.pv_curtailment_kw * 0.25 for step in trajectory.steps)
    throughput = sum((step.flows.battery_charge_kw + step.flows.battery_discharge_kw) * 0.25
                     for step in trajectory.steps)
    peak = max(imports)
    if config.profile == "cost":
        if len(config.import_tariff_inr_per_kwh) != len(truth) or len(config.export_credit_inr_per_kwh) != len(truth):
            raise ValueError("cost profile rates missing")
        energy_cost = sum((imp * buy - exp * sell) * 0.25 for imp, exp, buy, sell in zip(
            imports, exports, config.import_tariff_inr_per_kwh, config.export_credit_inr_per_kwh))
        return energy_cost + config.demand_charge_inr_per_kw * peak + \
            config.curtailment_penalty_inr_per_kwh * curtailed + \
            config.battery_throughput_penalty_inr_per_kwh * throughput
    if config.profile == "peak":
        return peak + 1e-6 * curtailed
    return curtailed + 1e-6 * peak
