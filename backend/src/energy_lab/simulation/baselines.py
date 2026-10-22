"""Causal B0/B1 comparator schedules; neither reads future hidden truth.

B0 serves obligations at their earliest declared times. B1 prefers local 10:00–
16:00 for EV charging and a contiguous pump run, then falls back within each
asset's window. These are declared heuristics, not optimizers. Both leave the
battery idle and use minimum permitted HVAC power. Replay is the validity gate.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from energy_lab.core.assets import SiteConfig
from energy_lab.core.time import TimeInterval, utc_to_local, validate_contiguous

from .engine import CandidateScheduleStep, InfeasibleSchedule, Trajectory, TruthDisturbance, simulate


@dataclass(frozen=True, slots=True)
class BaselinePlan:
    label: str
    information_set: str
    schedule: tuple[CandidateScheduleStep, ...]


def _solar_hour(interval: TimeInterval, timezone: str) -> bool:
    hour = utc_to_local(interval.start, timezone).hour
    return 10 <= hour < 16


def _ordered_indices(site: SiteConfig, intervals: tuple[TimeInterval, ...], window, policy: str) -> list[int]:
    eligible = [index for index, interval in enumerate(intervals) if window.contains(interval)]
    if policy == "B1":
        eligible.sort(key=lambda index: (not _solar_hour(intervals[index], site.timezone), index))
    return eligible


def build_baseline(site: SiteConfig, intervals: tuple[TimeInterval, ...], *, policy: str) -> BaselinePlan:
    """Choose B0/B1 actions from static obligations and local calendar only."""
    if policy not in {"B0", "B1"}:
        raise ValueError("baseline policy must be B0 or B1")
    validate_contiguous(intervals, required_minutes=15)
    ev_actions: list[dict[str, float]] = [{} for _ in intervals]
    pump_actions: list[dict[str, bool]] = [{} for _ in intervals]
    hvac_actions: list[dict[str, float]] = [{} for _ in intervals]

    for ev in site.evs:
        remaining = ev.required_energy_kwh
        for index in _ordered_indices(site, intervals, ev.window, policy):
            if remaining <= 1e-9:
                break
            duration = intervals[index].duration.hours
            power = min(ev.max_power_kw, remaining / (duration * ev.charger_efficiency))
            ev_actions[index][ev.asset_id] = power
            remaining -= power * duration * ev.charger_efficiency
        if remaining > 1e-6:
            raise InfeasibleSchedule(f"baseline {policy}: EV {ev.asset_id} service cannot fit in window")

    for pump in site.pumps:
        eligible = [index for index, interval in enumerate(intervals) if pump.window.contains(interval)]
        required = math.ceil((pump.required_runtime_hours - 1e-9) / 0.25)
        if required == 0:
            continue
        block_size = max(required, pump.minimum_run_intervals)
        if block_size > len(eligible):
            raise InfeasibleSchedule(f"baseline {policy}: pump {pump.asset_id} service cannot fit in window")
        blocks = [eligible[start:start + block_size] for start in range(len(eligible) - block_size + 1)]
        blocks = [block for block in blocks if all(b == a + 1 for a, b in zip(block, block[1:]))]
        if not blocks:
            raise InfeasibleSchedule(f"baseline {policy}: pump {pump.asset_id} has no contiguous service block")
        if policy == "B1":
            blocks.sort(key=lambda block: (-sum(_solar_hour(intervals[i], site.timezone) for i in block), block[0]))
        for index in blocks[0]:
            pump_actions[index][pump.asset_id] = True

    for hvac in site.hvacs:
        for index, interval in enumerate(intervals):
            if any(window.contains(interval) for window in hvac.windows):
                hvac_actions[index][hvac.asset_id] = hvac.min_power_kw

    schedule = tuple(CandidateScheduleStep(interval, ev_power_kw=ev_actions[index],
                                           pump_on=pump_actions[index], hvac_power_kw=hvac_actions[index])
                     for index, interval in enumerate(intervals))
    info = "declared asset obligations and fixed times" if policy == "B0" else "declared obligations and local solar-hour calendar"
    return BaselinePlan(policy, info, schedule)


def evaluate_baseline(site: SiteConfig, truth: tuple[TruthDisturbance, ...], *, seed: int, policy: str) -> tuple[BaselinePlan, Trajectory]:
    """Replay on truth only after the schedule has been fixed without reading it."""
    plan = build_baseline(site, tuple(item.interval for item in truth), policy=policy)
    return plan, simulate(site, truth, seed, plan.schedule)
