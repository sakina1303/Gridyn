"""One joint Pyomo model for balance, storage, flexible service and site limits.

The model may relax SOC or service for named upper-bound envelope passes only.
An operational candidate must pass the independent deterministic simulator.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import pyomo.environ as pyo

from energy_lab.core.assets import SiteConfig
from energy_lab.core.time import validate_contiguous
from energy_lab.simulation.engine import CandidateScheduleStep, TruthDisturbance


@dataclass(frozen=True, slots=True)
class ModelInput:
    site: SiteConfig
    disturbances: tuple[TruthDisturbance, ...]
    mode: str = "operational"  # theoretical, technical, operational

    def __post_init__(self) -> None:
        if self.mode not in {"theoretical", "technical", "operational"}:
            raise ValueError("invalid joint-model mode")
        if not self.disturbances:
            raise ValueError("joint model needs disturbances")
        validate_contiguous(tuple(item.interval for item in self.disturbances), required_minutes=15)
        if any(item.pv_available_kw > self.site.pv.ac_capacity_kw + 1e-9 for item in self.disturbances):
            raise ValueError("PV truth exceeds configured capacity")


def build_joint_model(inputs: ModelInput):
    site, truth, mode = inputs.site, inputs.disturbances, inputs.mode
    n = len(truth)
    dt = 0.25
    m = pyo.ConcreteModel()
    m.T = pyo.RangeSet(0, n - 1)
    m.B = pyo.RangeSet(0, n)
    m.import_kw = pyo.Var(m.T, domain=pyo.NonNegativeReals, bounds=(0, site.grid.import_limit_kw))
    m.export_kw = pyo.Var(m.T, domain=pyo.NonNegativeReals, bounds=(0, site.grid.export_limit_kw))
    m.grid_import_mode = pyo.Var(m.T, domain=pyo.Binary)
    m.pv_used_kw = pyo.Var(m.T, domain=pyo.NonNegativeReals)
    m.charge_kw = pyo.Var(m.T, domain=pyo.NonNegativeReals)
    m.discharge_kw = pyo.Var(m.T, domain=pyo.NonNegativeReals)
    m.battery_charge_mode = pyo.Var(m.T, domain=pyo.Binary)
    m.EV = pyo.Set(initialize=[ev.asset_id for ev in site.evs])
    m.PUMP = pyo.Set(initialize=[pump.asset_id for pump in site.pumps])
    m.HVAC = pyo.Set(initialize=[hvac.asset_id for hvac in site.hvacs])
    m.ev_kw = pyo.Var(m.EV, m.T, domain=pyo.NonNegativeReals)
    m.pump_on = pyo.Var(m.PUMP, m.T, domain=pyo.Binary)
    m.hvac_kw = pyo.Var(m.HVAC, m.T, domain=pyo.NonNegativeReals)
    m.limits = pyo.ConstraintList()

    for t, item in enumerate(truth):
        m.limits.add(m.import_kw[t] <= site.grid.import_limit_kw * m.grid_import_mode[t])
        m.limits.add(m.export_kw[t] <= site.grid.export_limit_kw * (1 - m.grid_import_mode[t]))
        m.limits.add(m.pv_used_kw[t] <= item.pv_available_kw)
        if not site.pv.allow_curtailment:
            m.limits.add(m.pv_used_kw[t] == item.pv_available_kw)
        if site.battery is None:
            m.charge_kw[t].fix(0)
            m.discharge_kw[t].fix(0)
        else:
            battery = site.battery
            m.limits.add(m.charge_kw[t] <= battery.max_charge_kw * m.battery_charge_mode[t])
            m.limits.add(m.discharge_kw[t] <= battery.max_discharge_kw * (1 - m.battery_charge_mode[t]))
            if battery.max_ramp_kw_per_hour is not None and mode != "theoretical":
                current = m.discharge_kw[t] - m.charge_kw[t]
                previous = 0 if t == 0 else m.discharge_kw[t - 1] - m.charge_kw[t - 1]
                m.limits.add(current - previous <= battery.max_ramp_kw_per_hour * dt)
                m.limits.add(previous - current <= battery.max_ramp_kw_per_hour * dt)

        flexible = 0
        for ev in site.evs:
            var = m.ev_kw[ev.asset_id, t]
            eligible = ev.window.contains(item.interval)
            m.limits.add(var <= ev.max_power_kw if eligible else var == 0)
            if ev.max_ramp_kw_per_hour is not None and mode == "operational":
                previous = 0 if t == 0 else m.ev_kw[ev.asset_id, t - 1]
                m.limits.add(var - previous <= ev.max_ramp_kw_per_hour * dt)
                m.limits.add(previous - var <= ev.max_ramp_kw_per_hour * dt)
            flexible += var
        for pump in site.pumps:
            var = m.pump_on[pump.asset_id, t]
            if not pump.window.contains(item.interval):
                var.fix(0)
            flexible += pump.rated_power_kw * var
        for hvac in site.hvacs:
            var = m.hvac_kw[hvac.asset_id, t]
            active = any(window.contains(item.interval) for window in hvac.windows)
            if active:
                m.limits.add(var <= hvac.max_power_kw)
                if mode == "operational":
                    m.limits.add(var >= hvac.min_power_kw)
            else:
                var.fix(0)
            if hvac.max_ramp_kw_per_hour is not None and mode == "operational":
                previous = 0 if t == 0 else m.hvac_kw[hvac.asset_id, t - 1]
                m.limits.add(var - previous <= hvac.max_ramp_kw_per_hour * dt)
                m.limits.add(previous - var <= hvac.max_ramp_kw_per_hour * dt)
            flexible += var
        m.limits.add(m.pv_used_kw[t] + m.import_kw[t] + m.discharge_kw[t] ==
                     item.critical_load_kw + item.fixed_load_kw + flexible + m.charge_kw[t] + m.export_kw[t])

    if site.battery and mode != "theoretical":
        battery = site.battery
        # Keep active transitions inside the exact simulator bounds despite
        # solver floating-point feasibility slack. Idle states at an initial
        # boundary remain valid; this tightens the optimization, not replay.
        soc_guard_kwh = 1e-4
        m.energy_kwh = pyo.Var(m.B, domain=pyo.NonNegativeReals,
                               bounds=(battery.min_energy_kwh, battery.max_energy_kwh))
        m.energy_kwh[0].fix(battery.initial_energy_kwh)
        for t in range(n):
            m.limits.add(m.energy_kwh[t + 1] == m.energy_kwh[t] +
                         dt * (battery.charge_efficiency * m.charge_kw[t] -
                               m.discharge_kw[t] / battery.discharge_efficiency))
            if battery.max_discharge_kw > 0:
                m.limits.add(m.energy_kwh[t + 1] >= battery.min_energy_kwh +
                             soc_guard_kwh * m.discharge_kw[t] / battery.max_discharge_kw)
            if battery.max_charge_kw > 0:
                m.limits.add(m.energy_kwh[t + 1] <= battery.max_energy_kwh -
                             soc_guard_kwh * m.charge_kw[t] / battery.max_charge_kw)
        terminal_guard = min(soc_guard_kwh,
                             max(0.0, battery.max_energy_kwh - battery.terminal_requirement_kwh))
        throughput_kwh = sum((m.charge_kw[t] + m.discharge_kw[t]) * dt for t in range(n))
        m.limits.add(m.energy_kwh[n] >= battery.terminal_requirement_kwh +
                     terminal_guard * throughput_kwh / battery.nominal_capacity_kwh)

    if mode == "operational":
        for ev in site.evs:
            m.limits.add(sum(m.ev_kw[ev.asset_id, t] * dt * ev.charger_efficiency for t in range(n))
                         == ev.required_energy_kwh)
        for pump in site.pumps:
            needed = math.ceil((pump.required_runtime_hours - 1e-9) / dt)
            eligible = sum(pump.window.contains(item.interval) for item in truth)
            if needed > eligible:
                raise ValueError(f"pump {pump.asset_id} runtime cannot fit in window")
            # No extra pump work is treated as free response capacity.
            m.limits.add(sum(m.pump_on[pump.asset_id, t] for t in range(n)) == needed)
            if pump.minimum_run_intervals > 1:
                for t in range(n):
                    start = m.pump_on[pump.asset_id, t] - (0 if t == 0 else m.pump_on[pump.asset_id, t - 1])
                    for offset in range(pump.minimum_run_intervals):
                        if t + offset < n:
                            m.limits.add(start <= m.pump_on[pump.asset_id, t + offset])
                        else:
                            m.limits.add(start <= 0)
    return m


def extract_schedule(model, truth: tuple[TruthDisturbance, ...], site: SiteConfig) -> tuple[CandidateScheduleStep, ...]:
    def clean(value: float) -> float:
        value = float(pyo.value(value))
        return 0.0 if abs(value) <= 1e-8 else value

    return tuple(CandidateScheduleStep(
        item.interval,
        battery_charge_kw=clean(model.charge_kw[t]),
        battery_discharge_kw=clean(model.discharge_kw[t]),
        ev_power_kw={ev.asset_id: clean(model.ev_kw[ev.asset_id, t]) for ev in site.evs},
        pump_on={pump.asset_id: bool(round(pyo.value(model.pump_on[pump.asset_id, t]))) for pump in site.pumps},
        hvac_power_kw={hvac.asset_id: clean(model.hvac_kw[hvac.asset_id, t]) for hvac in site.hvacs},
    ) for t, item in enumerate(truth))
