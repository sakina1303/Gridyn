"""Score a fixed response commitment against held-out or declared stresses."""

from __future__ import annotations

import math
from dataclasses import dataclass

from energy_lab.core.assets import SiteConfig
from energy_lab.simulation.engine import CandidateScheduleStep, InfeasibleSchedule, TruthDisturbance, simulate

from .scenarios import StressSpec, apply_stress


@dataclass(frozen=True, slots=True)
class ScenarioOutcome:
    scenario_id: str
    success: bool
    delivered_sustained_kw: float | None
    failure_reason: str | None


@dataclass(frozen=True, slots=True)
class CommitmentScore:
    promised_kw: float
    direction: str
    sample_count: int
    success_count: int
    success_fraction: float
    wilson_lower_95: float | None
    evidence_label: str
    tested_reliable_kw: float | None
    outcomes: tuple[ScenarioOutcome, ...]


def _wilson_lower(success: int, total: int) -> float:
    z = 1.96
    proportion = success / total
    denominator = 1 + z * z / total
    center = proportion + z * z / (2 * total)
    margin = z * math.sqrt(proportion * (1 - proportion) / total + z * z / (4 * total * total))
    return max(0.0, (center - margin) / denominator)


def score_commitment(
    site: SiteConfig, truth: tuple[TruthDisturbance, ...],
    baseline_schedule: tuple[CandidateScheduleStep, ...],
    committed_schedule: tuple[CandidateScheduleStep, ...],
    specs: tuple[StressSpec, ...], *, seed: int, promised_kw: float,
    direction: str, start_index: int, duration_intervals: int,
    target_fraction: float = 0.9,
    calibrated_holdout: bool = False,
) -> CommitmentScore:
    if not specs or len({item.scenario_id for item in specs}) != len(specs):
        raise ValueError("at least one uniquely identified scenario is required")
    if promised_kw < 0 or direction not in {"up", "down"}:
        raise ValueError("invalid response commitment")
    if not 0 < target_fraction <= 1:
        raise ValueError("target fraction must be in (0,1]")
    if start_index < 0 or duration_intervals < 1 or start_index + duration_intervals > len(truth):
        raise ValueError("response window outside truth horizon")
    if calibrated_holdout and any(item.provenance != "sampled_holdout" for item in specs):
        raise ValueError("calibrated holdout requires sampled_holdout provenance for every scenario")
    outcomes: list[ScenarioOutcome] = []
    for spec in specs:
        stressed_site, stressed_truth = apply_stress(site, truth, spec)
        try:
            baseline = simulate(stressed_site, stressed_truth, seed, baseline_schedule)
            committed = simulate(stressed_site, stressed_truth, seed, committed_schedule)
            delivered = min(
                baseline.steps[t].flows.grid_import_kw - committed.steps[t].flows.grid_import_kw
                if direction == "down" else
                committed.steps[t].flows.grid_import_kw - baseline.steps[t].flows.grid_import_kw
                for t in range(start_index, start_index + duration_intervals)
            )
            success = delivered + 1e-6 >= promised_kw
            outcomes.append(ScenarioOutcome(spec.scenario_id, success, max(0.0, delivered),
                                            None if success else "sustained response below commitment"))
        except InfeasibleSchedule as exc:
            outcomes.append(ScenarioOutcome(spec.scenario_id, False, None, str(exc)))
    count = sum(item.success for item in outcomes)
    fraction = count / len(outcomes)
    lower = _wilson_lower(count, len(outcomes)) if calibrated_holdout else None
    reliable = promised_kw if calibrated_holdout and lower is not None and lower >= target_fraction else None
    label = "held-out synthetic sample" if calibrated_holdout else "declared stress-set pass rate; statistical reliability unknown"
    return CommitmentScore(promised_kw, direction, len(outcomes), count, fraction,
                           lower, label, reliable, tuple(outcomes))
