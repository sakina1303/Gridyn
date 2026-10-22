"""Joint sustained import-response envelope with recovery-horizon replay."""

from __future__ import annotations

from dataclasses import dataclass

import pyomo.environ as pyo

from energy_lab.core.assets import SiteConfig
from energy_lab.optimization.constraints import ModelInput, build_joint_model, extract_schedule
from energy_lab.simulation.engine import CandidateScheduleStep, InfeasibleSchedule, Trajectory, TruthDisturbance, simulate


@dataclass(frozen=True, slots=True)
class EnvelopePass:
    mode: str
    status: str
    sustained_kw: float | None
    solver_termination: str


@dataclass(frozen=True, slots=True)
class EnvelopeResult:
    direction: str
    start_index: int
    duration_intervals: int
    passes: tuple[EnvelopePass, ...]
    operational_schedule: tuple[CandidateScheduleStep, ...] | None
    operational_trajectory: Trajectory | None
    recovery_import_delta_kwh: float | None
    reliable_kw: None = None  # Held-out calibration is a later phase.
    method: str = "joint Pyomo/HiGHS perfect-information oracle"

    def pass_for(self, mode: str) -> EnvelopePass:
        return next(item for item in self.passes if item.mode == mode)


def assess_envelope(
    site: SiteConfig,
    truth: tuple[TruthDisturbance, ...],
    baseline_schedule: tuple[CandidateScheduleStep, ...],
    *, seed: int, start_index: int, duration_intervals: int, direction: str,
    solver_time_limit_s: float = 30.0,
) -> EnvelopeResult:
    """Maximize constant response over a window, retaining the full recovery horizon.

    This uses future truth and is therefore an oracle research bound, not a
    deployable forecast-based commitment.
    """
    if direction not in {"up", "down"}:
        raise ValueError("direction must be up or down")
    if start_index < 0 or duration_intervals < 1 or start_index + duration_intervals > len(truth):
        raise ValueError("response window outside horizon")
    if solver_time_limit_s <= 0:
        raise ValueError("solver time limit must be positive")
    baseline = simulate(site, truth, seed, baseline_schedule)
    baseline_import = tuple(step.flows.grid_import_kw for step in baseline.steps)
    passes: list[EnvelopePass] = []
    operational_schedule = None
    operational_trajectory = None
    recovery_delta = None
    for mode in ("theoretical", "technical", "operational"):
        model = build_joint_model(ModelInput(site, truth, mode))
        model.q_kw = pyo.Var(domain=pyo.NonNegativeReals,
                             bounds=(0, site.grid.import_limit_kw))
        model.response = pyo.ConstraintList()
        for t in range(start_index, start_index + duration_intervals):
            if direction == "down":
                model.response.add(model.import_kw[t] <= baseline_import[t] - model.q_kw)
            else:
                model.response.add(model.import_kw[t] >= baseline_import[t] + model.q_kw)
        model.objective = pyo.Objective(expr=model.q_kw, sense=pyo.maximize)
        solver = pyo.SolverFactory("appsi_highs")
        solver.options["time_limit"] = solver_time_limit_s
        solver.options["mip_rel_gap"] = 0.01
        try:
            solved = solver.solve(model)
            termination = str(solved.solver.termination_condition)
        except (RuntimeError, ValueError) as exc:
            passes.append(EnvelopePass(mode, "infeasible_or_failed", None, str(exc)))
            continue
        if termination != "optimal":
            passes.append(EnvelopePass(mode, "no_validated_optimum", None, termination))
            continue
        q = max(0.0, float(pyo.value(model.q_kw)))
        if mode == "operational":
            schedule = extract_schedule(model, truth, site)
            try:
                trajectory = simulate(site, truth, seed, schedule)
            except InfeasibleSchedule as exc:
                passes.append(EnvelopePass(mode, "failed_independent_replay", None, str(exc)))
                continue
            response_values = [
                baseline_import[t] - trajectory.steps[t].flows.grid_import_kw if direction == "down" else
                trajectory.steps[t].flows.grid_import_kw - baseline_import[t]
                for t in range(start_index, start_index + duration_intervals)
            ]
            if any(value + 1e-6 < q for value in response_values):
                passes.append(EnvelopePass(mode, "failed_independent_response", None,
                                           "replayed grid response below optimized q"))
                continue
            operational_schedule = schedule
            operational_trajectory = trajectory
            recovery_delta = sum(
                (trajectory.steps[t].flows.grid_import_kw - baseline_import[t]) * 0.25
                for t in range(start_index + duration_intervals, len(truth))
            )
        passes.append(EnvelopePass(mode, "optimal", q, termination))
    return EnvelopeResult(direction, start_index, duration_intervals, tuple(passes),
                          operational_schedule, operational_trajectory, recovery_delta)
