"""HiGHS solver adapter with explicit infeasible and validation statuses."""

from __future__ import annotations

import time
from dataclasses import dataclass

import highspy
import pyomo
import pyomo.environ as pyo

from energy_lab.core.assets import SiteConfig
from energy_lab.simulation.engine import CandidateScheduleStep, TruthDisturbance

from .constraints import ModelInput, build_joint_model, extract_schedule
from .objectives import ObjectiveConfig, attach_objective
from .validate import ValidationResult, validate_schedule


@dataclass(frozen=True, slots=True)
class SolverRun:
    status: str
    termination: str
    schedule: tuple[CandidateScheduleStep, ...] | None
    validation: ValidationResult | None
    solver_objective: float | None
    gap: float | None
    runtime_s: float
    solver_version: str
    pyomo_version: str
    message: str | None = None


def solve_schedule(
    site: SiteConfig, truth: tuple[TruthDisturbance, ...], config: ObjectiveConfig,
    *, seed: int, time_limit_s: float = 30.0, relative_gap: float = 0.01,
) -> SolverRun:
    if time_limit_s <= 0 or not 0 <= relative_gap < 1:
        raise ValueError("invalid solver time limit or relative gap")
    model = build_joint_model(ModelInput(site, truth, "operational"))
    attach_objective(model, truth, config)
    solver = pyo.SolverFactory("appsi_highs")
    solver.options["time_limit"] = time_limit_s
    solver.options["mip_rel_gap"] = relative_gap
    started = time.monotonic()
    version = highspy.Highs().version()
    try:
        result = solver.solve(model)
        termination = str(result.solver.termination_condition)
    except (RuntimeError, ValueError) as exc:
        return SolverRun("infeasible_or_failed", "no_solution", None, None, None, None,
                         time.monotonic() - started, version, pyomo.version.version, str(exc))
    elapsed = time.monotonic() - started
    if termination != "optimal":
        return SolverRun("no_validated_solution", termination, None, None, None, None,
                         elapsed, version, pyomo.version.version)
    try:
        schedule = extract_schedule(model, truth, site)
        claimed = float(pyo.value(model.objective))
        validation = validate_schedule(site, truth, seed, schedule, config, claimed_objective=claimed)
    except (ValueError, RuntimeError) as exc:
        return SolverRun("failed_validation", termination, None, None, None, None,
                         elapsed, version, pyomo.version.version, str(exc))
    return SolverRun("optimal_validated", termination, schedule, validation, claimed, 0.0,
                     elapsed, version, pyomo.version.version)
