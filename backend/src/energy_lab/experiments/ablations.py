"""Paired observation ablation with causal previous-day forecasts.

The hidden truth is used only after the forecast and schedule are fixed. Failed
replay and abstention are outcomes, not discarded samples.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from energy_lab.core.time import require_utc
from energy_lab.flexibility.envelope import assess_envelope
from energy_lab.forecasting.baseline import issue_forecast
from energy_lab.simulation.baselines import build_baseline
from energy_lab.simulation.engine import InfeasibleSchedule, TruthDisturbance, simulate
from energy_lab.simulation.generator import GeneratedTruth
from energy_lab.simulation.observer import ObservationConfig, observe_truth


TARGETS = ("pv_available_kw", "critical_load_kw", "fixed_load_kw")


@dataclass(frozen=True, slots=True)
class AblationResult:
    observation_dataset_id: str
    truth_sha256: str
    observed_sha256: str
    issue_at_utc: datetime
    status: str
    reason: str | None
    estimated_sustained_kw: float | None
    realized_sustained_kw: float | None
    overstatement_kw: float | None
    synthetic: bool = True


def run_paired_ablation(
    generated: GeneratedTruth,
    configs: tuple[ObservationConfig, ...],
    *, issue_at_utc: datetime, horizon_intervals: int,
    start_index: int, duration_intervals: int, direction: str,
    seed: int,
) -> tuple[AblationResult, ...]:
    issue = require_utc(issue_at_utc, "decision issue")
    if horizon_intervals < 1:
        raise ValueError("horizon must contain intervals")
    future = tuple(item for item in generated.disturbances if item.interval.start >= issue)[:horizon_intervals]
    if len(future) != horizon_intervals or future[0].interval.start != issue:
        raise ValueError("decision issue must align with a complete truth horizon")
    if start_index < 0 or duration_intervals < 1 or start_index + duration_intervals > horizon_intervals:
        raise ValueError("response window outside forecast horizon")
    intervals = tuple(item.interval for item in future)
    site = generated.site
    outcomes: list[AblationResult] = []
    for config in configs:
        q: float | None = None
        observed = observe_truth(generated, config).observed
        def result(status: str, reason: str | None = None, estimate: float | None = None,
                   realized: float | None = None) -> AblationResult:
            overstatement = None if estimate is None else max(0.0, estimate - (realized or 0.0))
            return AblationResult(config.dataset_id, generated.manifest.truth_sha256,
                                  observed.manifest.observed_sha256, issue, status, reason,
                                  estimate, realized, overstatement)
        try:
            forecasts = {
                target: issue_forecast(observed.records, target=target, method="previous_day",
                                       issue_at_utc=issue, intervals=intervals,
                                       site_timezone=site.timezone)
                for target in TARGETS
            }
        except ValueError as exc:
            outcomes.append(result("abstained", str(exc)))
            continue
        try:
            estimate_truth = tuple(TruthDisturbance(
                interval,
                forecasts["pv_available_kw"].values_kw[index],
                forecasts["critical_load_kw"].values_kw[index],
                forecasts["fixed_load_kw"].values_kw[index],
            ) for index, interval in enumerate(intervals))
            baseline = build_baseline(site, intervals, policy="B0")
            estimated = assess_envelope(site, estimate_truth, baseline.schedule, seed=seed,
                                        start_index=start_index, duration_intervals=duration_intervals,
                                        direction=direction)
            operational = estimated.pass_for("operational")
            if operational.status != "optimal" or estimated.operational_schedule is None:
                outcomes.append(result("abstained", f"forecast model: {operational.status}"))
                continue
            q = operational.sustained_kw
            actual_baseline = simulate(site, future, seed, baseline.schedule)
            actual_schedule = simulate(site, future, seed, estimated.operational_schedule)
            differences = [
                actual_baseline.steps[t].flows.grid_import_kw - actual_schedule.steps[t].flows.grid_import_kw
                if direction == "down" else
                actual_schedule.steps[t].flows.grid_import_kw - actual_baseline.steps[t].flows.grid_import_kw
                for t in range(start_index, start_index + duration_intervals)
            ]
            realized = max(0.0, min(differences))
            outcomes.append(result("delivered" if realized + 1e-6 >= q else "overstated",
                                   None, q, realized))
        except (ValueError, InfeasibleSchedule) as exc:
            outcomes.append(result("delivery_failure" if q is not None else "abstained",
                                   str(exc), q))
    return tuple(outcomes)
