"""Declared synthetic response stresses replayed against the canonical simulator.

This is a model stress audit, not an estimate of field reliability. A fixed
schedule is committed before each hidden-truth perturbation is applied.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, replace
from datetime import datetime, timezone

from energy_lab.core.assets import (BatteryConfig, EVConfig, GridConfig, HVACConfig,
                                    PVConfig, PumpConfig, SiteConfig)
from energy_lab.core.time import TimeInterval, TimeWindow, make_intervals
from energy_lab.core.units import balance_tolerance_kw
from energy_lab.simulation.baselines import build_baseline
from energy_lab.simulation.engine import (CandidateScheduleStep, InfeasibleSchedule,
                                          TruthDisturbance, simulate)
from energy_lab.uncertainty.scenarios import StressSpec, apply_stress


SEEDS = (7, 11, 19)
DURATIONS = (4, 8, 16)  # 1, 2 and 4 hours at 15-minute resolution.
PROMISED_KW = {"down": 2.0, "up": 1.5}


@dataclass(frozen=True, slots=True)
class MatrixCase:
    factor: str
    level: str
    stress: StressSpec | None = None
    peak_shift_intervals: int = 0
    evaluable: bool = True
    reason: str | None = None


def declared_cases(initial_energy_kwh: float, minimum_energy_kwh: float,
                   maximum_energy_kwh: float) -> tuple[MatrixCase, ...]:
    headroom = initial_energy_kwh - minimum_energy_kwh
    cases = [MatrixCase("control", "clean", StressSpec("clean"))]
    for factor in (0.75, 0.5, 0.25):
        cases.append(MatrixCase("PV truth deviation", f"output-{factor:.2f}",
                                StressSpec(f"pv-{factor}", pv_factor=factor)))
    for factor in (1.05, 1.10, 1.20):
        cases.append(MatrixCase("load magnitude", f"load-{factor:.2f}",
                                StressSpec(f"load-{factor}", critical_load_factor=factor,
                                           fixed_load_factor=factor)))
    for factor in (0.75, 0.50, 0.10):
        cases.append(MatrixCase("load magnitude", f"load-{factor:.2f}",
                                StressSpec(f"load-{factor}", critical_load_factor=factor,
                                           fixed_load_factor=factor)))
    for hours in (-3, -2, -1, 1, 2, 3):
        cases.append(MatrixCase("load peak timing", f"shift-{hours:+d}h",
                                peak_shift_intervals=hours * 4))
    for fraction in (0.75, 0.5, 0.25):
        cases.append(MatrixCase("initial battery SOC", f"headroom-{fraction:.2f}",
                                StressSpec(f"soc-{fraction}",
                                    initial_battery_energy_kwh=minimum_energy_kwh + headroom * fraction)))
    for remaining_fraction in (0.75, 0.5, 0.25):
        cases.append(MatrixCase("high initial battery SOC", f"charge-room-{remaining_fraction:.2f}",
                                StressSpec(f"high-soc-{remaining_fraction}",
                                    initial_battery_energy_kwh=maximum_energy_kwh -
                                        (maximum_energy_kwh - initial_energy_kwh) * remaining_fraction)))
    for shift in (1, 2, 3):
        cases.append(MatrixCase("EV arrival", f"late-{shift * 15}m",
                                StressSpec(f"ev-arrival-{shift}", ev_arrival_shift_intervals=shift)))
        cases.append(MatrixCase("EV departure", f"early-{shift * 15}m",
                                StressSpec(f"ev-departure-{shift}", ev_departure_shift_intervals=-shift)))
    for factor in (1.05, 1.10, 1.20):
        cases.append(MatrixCase("EV service demand", f"required-{factor:.2f}",
                                StressSpec(f"ev-required-{factor}", ev_required_factor=factor)))
    for factor in (1.25, 1.5, 2.0):
        cases.append(MatrixCase("pump runtime", f"runtime-{factor:.2f}",
                                StressSpec(f"pump-runtime-{factor}", pump_runtime_factor=factor)))
    for factor in (0.75, 0.5, 0.25):
        cases.append(MatrixCase("battery discharge rating", f"rating-{factor:.2f}",
                                StressSpec(f"battery-rating-{factor}", battery_discharge_factor=factor)))
    for delta in (1, 2, 3):
        cases.append(MatrixCase("outdoor temperature", f"warmer-{delta}C",
                                StressSpec(f"temperature-{delta}", outdoor_temperature_delta_c=delta),
                                evaluable=False,
                                reason="no thermal-state or comfort response model; HVAC power bounds alone cannot validate comfort"))
    for pv_factor, soc_fraction in ((0.75, 0.75), (0.5, 0.5), (0.25, 0.25)):
        cases.append(MatrixCase("PV and SOC interaction", f"pv-{pv_factor:.2f}-soc-{soc_fraction:.2f}",
                                StressSpec(f"pv-soc-{pv_factor}", pv_factor=pv_factor,
                                    initial_battery_energy_kwh=minimum_energy_kwh + headroom * soc_fraction)))
    cases.append(MatrixCase("tariff and EV interaction", "unavailable", evaluable=False,
                            reason="no verified applicable tariff or operator EV cost objective"))
    return tuple(cases)


def _fixture(seed: int) -> tuple[SiteConfig, tuple[TruthDisturbance, ...],
                                 tuple[TimeInterval, ...]]:
    rng = random.Random(seed)
    intervals = make_intervals(datetime(2026, 1, 1, 3, 30, tzinfo=timezone.utc), 32, 15)
    site = SiteConfig(
        f"declared-synthetic-{seed}", "Asia/Kolkata", GridConfig(24, 0), PVConfig(5),
        battery=BatteryConfig(20, 0.1, 0.9, 12, 4, 4, 0.9, 0.9),
        evs=(EVConfig("ev", TimeWindow(intervals[0].start, intervals[28].start), 2, 4),),
        pumps=(PumpConfig("pump", TimeWindow(intervals[2].start, intervals[-1].end), 2, 0.5),),
        hvacs=(HVACConfig("hvac", (TimeWindow(intervals[0].start, intervals[-1].end),), 1, 3),),
    )
    load_offset = rng.uniform(-0.08, 0.08)
    solar_offset = rng.uniform(-0.1, 0.1)
    truth = tuple(TruthDisturbance(
        interval,
        0 if index < 8 else (2 if index < 16 else 3) + solar_offset,
        9 + load_offset,
        9 + (4 if 12 <= index < 16 else 0),
        outdoor_temperature_c=30,
    ) for index, interval in enumerate(intervals))
    return site, truth, tuple(intervals)


def _committed_schedule(site: SiteConfig, intervals: tuple[TimeInterval, ...],
                        duration: int, direction: str) -> tuple[CandidateScheduleStep, ...]:
    baseline = build_baseline(site, intervals, policy="B0").schedule
    if direction == "down":
        # Discharge during response, then restore initial energy over the last
        # four hours. Shift declared EV and pump service within their windows.
        recovery_charge_kw = 2 * (duration * 0.25) / (0.9 * 0.9 * 4)
        return tuple(replace(step,
            battery_discharge_kw=2 if index < duration else 0,
            battery_charge_kw=recovery_charge_kw if index >= 16 else 0,
            ev_power_kw={"ev": 4} if index in (24, 25) else {},
            pump_on={"pump": True} if index in (28, 29) else {},
        ) for index, step in enumerate(baseline))
    if direction == "up":
        # Charge during the later response window and discharge the stored
        # energy over the final three hours to satisfy terminal SOC.
        # Leave a declared 0.00003 kWh terminal margin after three hours.
        recovery_discharge_kw = 1.5 * (duration * 0.25) * 0.9 * 0.9 / 3 - 1e-5
        return tuple(replace(step,
            battery_charge_kw=1.5 if 4 <= index < 4 + duration else 0,
            battery_discharge_kw=recovery_discharge_kw if index >= 20 else 0,
        ) for index, step in enumerate(baseline))
    raise ValueError("direction must be up or down")


def _shift_peak(truth: tuple[TruthDisturbance, ...], shift: int) -> tuple[TruthDisturbance, ...]:
    target = 12 + shift
    if target < 0 or target + 4 > len(truth):
        raise ValueError("shifted peak outside synthetic horizon")
    return tuple(replace(item, fixed_load_kw=item.fixed_load_kw - (4 if 12 <= index < 16 else 0)
                         + (4 if target <= index < target + 4 else 0))
                 for index, item in enumerate(truth))


def run_synthetic_matrix(*, seeds: tuple[int, ...] = SEEDS) -> dict:
    if not seeds or len(set(seeds)) != len(seeds):
        raise ValueError("matrix needs unique seeds")
    rows: list[dict] = []
    for seed in seeds:
        site, truth, intervals = _fixture(seed)
        for direction in ("down", "up"):
            for duration in DURATIONS:
                response_start = 0 if direction == "down" else 4
                promised_kw = PROMISED_KW[direction]
                baseline = build_baseline(site, intervals, policy="B0").schedule
                candidate = _committed_schedule(site, intervals, duration, direction)
                # This is a strict fixture gate; a broken control cannot yield results.
                simulate(site, truth, seed, baseline)
                simulate(site, truth, seed, candidate)
                for case in declared_cases(site.battery.initial_energy_kwh, site.battery.min_energy_kwh,
                                           site.battery.max_energy_kwh):
                    row = {"factor": case.factor, "level": case.level, "seed": seed,
                           "direction": direction, "response_duration_hours": duration * 0.25,
                           "response_start_interval": response_start, "promised_kw": promised_kw,
                           "status": "not_evaluable" if not case.evaluable else None,
                           "reason": case.reason, "delivered_sustained_kw": None,
                           "overstatement_kw": None, "recovery_import_delta_kwh": None,
                           "physical_balance_max_abs_kw": None}
                    if not case.evaluable:
                        rows.append(row)
                        continue
                    stressed_site, stressed_truth = apply_stress(site, truth, case.stress or StressSpec(case.level))
                    if case.peak_shift_intervals:
                        stressed_truth = _shift_peak(stressed_truth, case.peak_shift_intervals)
                    try:
                        reference = simulate(stressed_site, stressed_truth, seed, baseline)
                    except (InfeasibleSchedule, ValueError) as exc:
                        row.update(status="baseline_infeasible", reason=str(exc))
                        rows.append(row)
                        continue
                    try:
                        realized = simulate(stressed_site, stressed_truth, seed, candidate)
                    except (InfeasibleSchedule, ValueError) as exc:
                        row.update(status="candidate_infeasible", reason=str(exc))
                        rows.append(row)
                        continue
                    differences = [(reference.steps[index].flows.grid_import_kw -
                                    realized.steps[index].flows.grid_import_kw) if direction == "down" else
                                   (realized.steps[index].flows.grid_import_kw -
                                    reference.steps[index].flows.grid_import_kw)
                                   for index in range(response_start, response_start + duration)]
                    delivered = max(0.0, min(differences))
                    overstatement = max(0.0, promised_kw - delivered)
                    row.update(status="delivered" if overstatement <= balance_tolerance_kw(site.grid.import_limit_kw) else "overstated",
                               delivered_sustained_kw=delivered, overstatement_kw=overstatement,
                               recovery_import_delta_kwh=sum(
                                   (realized.steps[index].flows.grid_import_kw -
                                    reference.steps[index].flows.grid_import_kw) * 0.25
                                   for index in range(response_start + duration, len(truth))),
                               physical_balance_max_abs_kw=max(
                                   abs(step.flows.balance_residual_kw) for step in realized.steps))
                    rows.append(row)
    return {"schema_version": "1", "evidence_label": "declared synthetic model stress; field reliability unknown",
            "seeds": list(seeds), "response_durations_hours": [1, 2, 4],
            "directions": ["down", "up"], "promised_kw_by_direction": PROMISED_KW, "rows": rows,
            "limitations": ["Fixed hand-checkable candidate schedule, not a forecast-issued optimal policy.",
                            "The test uses seeded synthetic truth; repeated seeds are not independent field days.",
                            "Thermal comfort and tariff cost effects are not evaluable with the current canonical model and evidence.",
                            "No measured savings, field response reliability, or operator acceptance is inferred."]}
