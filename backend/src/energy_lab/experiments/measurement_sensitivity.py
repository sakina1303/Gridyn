"""Rank declared synthetic uncertainty sensitivities for a fixed commitment.

The ordering is a model diagnostic under stated ranges, not a sensor purchase
recommendation or an observed value-of-information estimate.
"""

from __future__ import annotations

from dataclasses import dataclass

from energy_lab.core.assets import SiteConfig
from energy_lab.simulation.engine import CandidateScheduleStep, TruthDisturbance
from energy_lab.uncertainty.calibration import score_commitment
from energy_lab.uncertainty.scenarios import StressSpec


@dataclass(frozen=True, slots=True)
class MeasurementSensitivity:
    measurement: str
    declared_range: str
    scenario_count: int
    failed_count: int
    maximum_response_shortfall_kw: float | None
    rank: int | None
    collection_request: str
    burden: None = None
    evidence_label: str = "synthetic model sensitivity, not field value"


@dataclass(frozen=True, slots=True)
class MeasurementSensitivityResult:
    promised_kw: float
    direction: str
    candidates: tuple[MeasurementSensitivity, ...]
    ranking_basis: str = "service/feasibility failures first, then maximum response shortfall"
    limitation: str = "declared stress ranges and unknown measurement burden; field priority unvalidated"


def assess_measurement_sensitivity(
    site: SiteConfig, truth: tuple[TruthDisturbance, ...],
    baseline_schedule: tuple[CandidateScheduleStep, ...],
    committed_schedule: tuple[CandidateScheduleStep, ...],
    *, seed: int, promised_kw: float, direction: str,
    start_index: int, duration_intervals: int,
) -> MeasurementSensitivityResult:
    if promised_kw <= 0:
        raise ValueError("positive committed response is required for sensitivity ranking")
    groups: list[tuple[str, str, tuple[StressSpec, ...]]] = []
    if site.pv.ac_capacity_kw > 0 and any(item.pv_available_kw > 0 for item in truth):
        groups.append(("PV output", "25%, 50%, 75% of synthetic PV trace", tuple(
            StressSpec(f"pv-{factor}", pv_factor=factor) for factor in (0.75, 0.5, 0.25))))
    groups.append(("Critical and fixed load", "105%, 110%, 120% of synthetic load trace", tuple(
        StressSpec(f"load-{factor}", critical_load_factor=factor, fixed_load_factor=factor)
        for factor in (1.05, 1.1, 1.2))))
    if site.battery and site.battery.initial_energy_kwh > site.battery.min_energy_kwh + 1e-9:
        minimum = site.battery.min_energy_kwh
        headroom = site.battery.initial_energy_kwh - minimum
        groups.append(("Battery state of charge", "25%, 50%, 75% of initial usable headroom", tuple(
            StressSpec(f"soc-{fraction}", initial_battery_energy_kwh=minimum + headroom * fraction)
            for fraction in (0.75, 0.5, 0.25))))
    if site.battery and site.battery.max_discharge_kw > 0:
        groups.append(("Battery discharge availability", "75%, 50%, 25% of declared AC rating", tuple(
            StressSpec(f"battery-rating-{factor}", battery_discharge_factor=factor)
            for factor in (0.75, 0.5, 0.25))))
    if site.evs:
        groups.append(("EV service requirement", "105%, 110%, 120% of declared energy", tuple(
            StressSpec(f"ev-{factor}", ev_required_factor=factor)
            for factor in (1.05, 1.1, 1.2))))

    rows: list[tuple[str, str, int, int, float | None]] = []
    for name, declared_range, specs in groups:
        score = score_commitment(site, truth, baseline_schedule, committed_schedule,
            specs, seed=seed, promised_kw=promised_kw, direction=direction,
            start_index=start_index, duration_intervals=duration_intervals)
        failures = sum(item.delivered_sustained_kw is None for item in score.outcomes)
        delivered = [item.delivered_sustained_kw for item in score.outcomes
                     if item.delivered_sustained_kw is not None]
        shortfall = max(0.0, promised_kw - min(delivered)) if delivered else None
        rows.append((name, declared_range, len(specs), failures, shortfall))
    rows.sort(key=lambda item: (-item[3], -(item[4] or 0), item[0]))
    collection_requests = {
        "PV output": "Check inverter output and available generation or curtailment logs at 15-minute resolution.",
        "Critical and fixed load": "Check site import and submetered load readings at 15-minute resolution.",
        "Battery state of charge": "Check timestamped battery SOC and AC charge/discharge power.",
        "Battery discharge availability": "Check discharge ratings, derating events and availability logs.",
        "EV service requirement": "Check arrival, departure and energy delivered for each charging session.",
    }
    ranked_items: list[MeasurementSensitivity] = []
    previous_key: tuple[int, float] | None = None
    current_rank = 0
    for index, (name, declared_range, count, failures, shortfall) in enumerate(rows):
        key = (failures, round(shortfall or 0.0, 6))
        if key != previous_key:
            current_rank = index + 1
        rank = current_rank if failures or (shortfall is not None and shortfall > 1e-6) else None
        ranked_items.append(MeasurementSensitivity(name, declared_range, count,
                                                   failures, shortfall, rank,
                                                   collection_requests[name]))
        previous_key = key
    ranked = tuple(ranked_items)
    return MeasurementSensitivityResult(promised_kw, direction, ranked)
