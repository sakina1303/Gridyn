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
    rule_status: str = "not_run"
    rule_peak_kw: float | None = None
    rule_import_kwh: float | None = None
    rule_reason: str | None = None
    baseline_reason: str | None = None


def compare_scenario(
    site: SiteConfig, truth: tuple[TruthDisturbance, ...], truth_sha256: str,
    config: ScenarioConfig, *, objective: ObjectiveConfig,
) -> PairedOutcome:
    changed_site = apply_scenario(site, config)
    if not truth_sha256:
        raise ValueError("paired truth checksum is required")
    intervals = tuple(item.interval for item in truth)

    def replay_rule(policy: str):
        try:
            plan = build_baseline(changed_site, intervals, policy=policy)
            trajectory = simulate(changed_site, truth, config.seed, plan.schedule)
            return "valid", max(step.flows.grid_import_kw for step in trajectory.steps), trajectory.grid_import_kwh, None
        except (ValueError, InfeasibleSchedule) as exc:
            return "infeasible", None, None, str(exc)

    baseline_status, baseline_peak, baseline_import, baseline_reason = replay_rule("B0")
    rule_status, rule_peak, rule_import, rule_reason = replay_rule("B1")
    solved = solve_schedule(changed_site, truth, objective, seed=config.seed)
    if solved.validation is None:
        return PairedOutcome(
            scenario_id=config.scenario_id, truth_sha256=truth_sha256,
            baseline_status=baseline_status, scenario_status=solved.status,
            baseline_peak_kw=baseline_peak, scenario_peak_kw=None, peak_delta_kw=None,
            baseline_import_kwh=baseline_import, scenario_import_kwh=None,
            reason=solved.message or baseline_reason,
            rule_status=rule_status, rule_peak_kw=rule_peak,
            rule_import_kwh=rule_import, rule_reason=rule_reason,
            baseline_reason=baseline_reason,
        )
    scenario_trace = solved.validation.trajectory
    scenario_peak = max(step.flows.grid_import_kw for step in scenario_trace.steps)
    return PairedOutcome(
        scenario_id=config.scenario_id, truth_sha256=truth_sha256,
        baseline_status=baseline_status, scenario_status="optimal_validated",
        baseline_peak_kw=baseline_peak, scenario_peak_kw=scenario_peak,
        peak_delta_kw=scenario_peak - baseline_peak if baseline_peak is not None else None,
        baseline_import_kwh=baseline_import, scenario_import_kwh=scenario_trace.grid_import_kwh,
        reason=None,
        rule_status=rule_status, rule_peak_kw=rule_peak,
        rule_import_kwh=rule_import, rule_reason=rule_reason,
        baseline_reason=baseline_reason,
    )
