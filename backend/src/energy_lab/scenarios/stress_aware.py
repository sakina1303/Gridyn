"""Choose a fixed synthetic schedule that survives declared training stresses.

This is candidate selection, not a globally optimal robust MILP. It uses
synthetic future traces and makes no calibrated reliability claim.
"""

from __future__ import annotations

from dataclasses import dataclass

from energy_lab.core.assets import SiteConfig
from energy_lab.optimization.objectives import ObjectiveConfig
from energy_lab.optimization.solve import solve_schedule
from energy_lab.simulation.baselines import build_baseline
from energy_lab.simulation.engine import CandidateScheduleStep, InfeasibleSchedule, TruthDisturbance, simulate
from energy_lab.uncertainty.scenarios import StressSpec, apply_stress

from .schema import ScenarioConfig, apply_scenario


@dataclass(frozen=True, slots=True)
class StressReplay:
    scenario_id: str
    status: str
    peak_import_kw: float | None
    reason: str | None


@dataclass(frozen=True, slots=True)
class StressAwareOutcome:
    status: str
    selected_source: str | None
    reference_peak_kw: float | None
    worst_training_peak_kw: float | None
    training: tuple[StressReplay, ...]
    evaluation: tuple[StressReplay, ...]
    candidate_count: int
    reason: str | None
    method: str = "fixed-schedule selection from validated candidates"
    evidence_label: str = "declared synthetic stresses; future-truth oracle; statistical reliability unknown"
    synthetic: bool = True
    selected_schedule: tuple[CandidateScheduleStep, ...] | None = None


def _replay(
    site: SiteConfig, truth: tuple[TruthDisturbance, ...],
    schedule: tuple[CandidateScheduleStep, ...], spec: StressSpec, seed: int,
) -> StressReplay:
    try:
        stressed_site, stressed_truth = apply_stress(site, truth, spec)
        trajectory = simulate(stressed_site, stressed_truth, seed, schedule)
        return StressReplay(spec.scenario_id, "valid",
                            max(step.flows.grid_import_kw for step in trajectory.steps), None)
    except (ValueError, InfeasibleSchedule) as exc:
        return StressReplay(spec.scenario_id, "infeasible", None, str(exc))


def select_stress_aware_schedule(
    site: SiteConfig, truth: tuple[TruthDisturbance, ...], config: ScenarioConfig,
    training_specs: tuple[StressSpec, ...], evaluation_specs: tuple[StressSpec, ...],
) -> StressAwareOutcome:
    if not truth or not training_specs or not evaluation_specs:
        raise ValueError("truth, training stresses and evaluation stresses are required")
    ids = [spec.scenario_id for spec in training_specs + evaluation_specs]
    if len(ids) != len(set(ids)):
        raise ValueError("training and evaluation stresses need distinct IDs")
    if any(spec.provenance != "declared_synthetic_stress" for spec in training_specs + evaluation_specs):
        raise ValueError("this selector accepts declared synthetic stresses only")
    changed_site = apply_scenario(site, config)
    intervals = tuple(item.interval for item in truth)
    candidates: list[tuple[str, tuple[CandidateScheduleStep, ...]]] = []
    for policy in ("B0", "B1"):
        try:
            candidates.append((policy, build_baseline(changed_site, intervals, policy=policy).schedule))
        except (ValueError, InfeasibleSchedule):
            pass
    for spec in training_specs:
        stressed_site, stressed_truth = apply_stress(changed_site, truth, spec)
        solved = solve_schedule(stressed_site, stressed_truth, ObjectiveConfig("peak"), seed=config.seed)
        if solved.status == "optimal_validated" and solved.schedule is not None:
            candidates.append((f"peak optimizer / {spec.scenario_id}", solved.schedule))

    best: tuple[float, str, tuple[CandidateScheduleStep, ...], tuple[StressReplay, ...]] | None = None
    for source, schedule in candidates:
        training = tuple(_replay(changed_site, truth, schedule, spec, config.seed)
                         for spec in training_specs)
        if any(item.status != "valid" for item in training):
            continue
        worst = max(item.peak_import_kw for item in training if item.peak_import_kw is not None)
        if best is None or worst < best[0] - 1e-7:
            best = (worst, source, schedule, training)
    if best is None:
        return StressAwareOutcome("no_validated_candidate", None, None, None, (), (),
                                  len(candidates), "No fixed candidate served every training stress.")

    worst, source, schedule, training = best
    reference = simulate(changed_site, truth, config.seed, schedule)
    evaluation = tuple(_replay(changed_site, truth, schedule, spec, config.seed)
                       for spec in evaluation_specs)
    return StressAwareOutcome(
        "selected", source,
        max(step.flows.grid_import_kw for step in reference.steps), worst,
        training, evaluation, len(candidates), None,
        selected_schedule=schedule,
    )


def declared_stress_sets(site: SiteConfig) -> tuple[tuple[StressSpec, ...], tuple[StressSpec, ...]]:
    """Small, explicit study settings; these are not learned probabilities."""
    training = (
        StressSpec("train-normal"),
        StressSpec("train-cloudy", pv_factor=0.5),
        StressSpec("train-high-demand", critical_load_factor=1.1, fixed_load_factor=1.1),
    )
    evaluation = (
        StressSpec("eval-very-cloudy", pv_factor=0.25),
        StressSpec("eval-higher-demand", critical_load_factor=1.2, fixed_load_factor=1.2),
        StressSpec("eval-combined", pv_factor=0.5,
                   critical_load_factor=1.1, fixed_load_factor=1.1),
    )
    if site.battery is not None:
        training += (StressSpec("train-low-soc",
                                initial_battery_energy_kwh=site.battery.min_energy_kwh),
                     StressSpec("train-battery-derated", battery_discharge_factor=0.75))
        evaluation += (StressSpec("eval-low-soc-cloudy", pv_factor=0.5,
                                  initial_battery_energy_kwh=site.battery.min_energy_kwh),
                       StressSpec("eval-battery-derated", battery_discharge_factor=0.5))
    return training, evaluation
