"""Independent model-output checker based on canonical simulator replay."""

from __future__ import annotations

from dataclasses import dataclass

from energy_lab.core.assets import SiteConfig
from energy_lab.simulation.engine import CandidateScheduleStep, Trajectory, TruthDisturbance, simulate

from .objectives import ObjectiveConfig, recompute_objective


@dataclass(frozen=True, slots=True)
class ValidationResult:
    trajectory: Trajectory
    recomputed_objective: float
    maximum_balance_residual_kw: float


def validate_schedule(
    site: SiteConfig, truth: tuple[TruthDisturbance, ...], seed: int,
    schedule: tuple[CandidateScheduleStep, ...], config: ObjectiveConfig,
    *, claimed_objective: float | None = None,
) -> ValidationResult:
    trajectory = simulate(site, truth, seed, schedule)
    objective = recompute_objective(trajectory, truth, config)
    residual = max(abs(step.flows.balance_residual_kw) for step in trajectory.steps)
    tolerance = max(1e-6, 1e-7 * site.grid.import_limit_kw)
    if residual > tolerance:
        raise ValueError("independent replay has physical balance residual")
    if claimed_objective is not None and abs(objective - claimed_objective) > max(1e-5, 1e-6 * abs(objective)):
        raise ValueError("solver objective differs from independently recomputed objective")
    return ValidationResult(trajectory, objective, residual)
