"""Paired baseline/optimized scenario outcomes on identical hidden truth."""

from __future__ import annotations

from dataclasses import dataclass

from energy_lab.core.assets import SiteConfig
from energy_lab.optimization.objectives import ObjectiveConfig
from energy_lab.optimization.solve import solve_schedule
from energy_lab.simulation.baselines import build_baseline
from energy_lab.simulation.engine import InfeasibleSchedule, TruthDisturbance, simulate

from .schema import ScenarioConfig, apply_scenario


@dataclass(frozen=True, slots=True)
class PairedOutcome:
    scenario_id: str
    truth_sha256: str
    baseline_status: str
    scenario_status: str
    baseline_peak_kw: float | None
    scenario_peak_kw: float | None
    peak_delta_kw: float | None
    baseline_import_kwh: float | None
    scenario_import_kwh: float | None
    reason: str | None
    synthetic: bool = True


def compare_scenario(
    site: SiteConfig, truth: tuple[TruthDisturbance, ...], truth_sha256: str,
    config: ScenarioConfig, *, objective: ObjectiveConfig,
) -> PairedOutcome:
    baseline_site = site
    changed_site = apply_scenario(site, config)
    if not truth_sha256:
        raise ValueError("paired truth checksum is required")
    plan = build_baseline(baseline_site, tuple(item.interval for item in truth), policy="B0")
    try:
        baseline = simulate(baseline_site, truth, config.seed, plan.schedule)
    except InfeasibleSchedule as exc:
        return PairedOutcome(config.scenario_id, truth_sha256, "infeasible", "not_run",
                             None, None, None, None, None, str(exc))
    baseline_peak = max(step.flows.grid_import_kw for step in baseline.steps)
    solved = solve_schedule(changed_site, truth, objective, seed=config.seed)
    if solved.validation is None:
        return PairedOutcome(config.scenario_id, truth_sha256, "valid", solved.status,
                             baseline_peak, None, None, baseline.grid_import_kwh, None, solved.message)
    scenario_trace = solved.validation.trajectory
    scenario_peak = max(step.flows.grid_import_kw for step in scenario_trace.steps)
    return PairedOutcome(config.scenario_id, truth_sha256, "valid", "optimal_validated",
                         baseline_peak, scenario_peak, scenario_peak - baseline_peak,
                         baseline.grid_import_kwh, scenario_trace.grid_import_kwh, None)
