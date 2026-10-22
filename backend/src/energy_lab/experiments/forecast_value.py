"""Paired decision-value study: the same optimizer, truth and objective."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from energy_lab.core.assets import SiteConfig
from energy_lab.core.time import require_utc
from energy_lab.forecasting.baseline import issue_forecast
from energy_lab.forecasting.tree import issue_tree_forecast
from energy_lab.optimization.objectives import ObjectiveConfig, recompute_objective
from energy_lab.optimization.solve import solve_schedule
from energy_lab.simulation.engine import InfeasibleSchedule, TruthDisturbance, simulate
from energy_lab.simulation.observer import ObservedRecord


TARGETS = ("pv_available_kw", "critical_load_kw", "fixed_load_kw")


@dataclass(frozen=True, slots=True)
class ForecastDecisionOutcome:
    method: str
    issue_at_utc: datetime
    training_end_utc: datetime | None
    forecast_mae_kw: float | None
    solver_status: str
    realized_objective: float | None
    oracle_objective: float | None
    regret: float | None
    failure_reason: str | None
    synthetic: bool = True


def compare_forecast_decisions(
    site: SiteConfig, observed: tuple[ObservedRecord, ...],
    actual_future: tuple[TruthDisturbance, ...], *, issue_at_utc: datetime,
    objective: ObjectiveConfig, seed: int,
    methods: tuple[str, ...] = ("previous_day", "random_forest"),
) -> tuple[ForecastDecisionOutcome, ...]:
    issue = require_utc(issue_at_utc, "forecast decision issue")
    if not actual_future or actual_future[0].interval.start != issue:
        raise ValueError("actual evaluation horizon must begin at decision issue")
    intervals = tuple(item.interval for item in actual_future)
    oracle = solve_schedule(site, actual_future, objective, seed=seed)
    oracle_value = oracle.validation.recomputed_objective if oracle.validation else None
    outcomes: list[ForecastDecisionOutcome] = []
    for method in methods:
        try:
            forecasts = {}
            for target in TARGETS:
                if method == "random_forest":
                    forecasts[target] = issue_tree_forecast(observed, target=target, issue_at_utc=issue,
                        intervals=intervals, site_timezone=site.timezone, seed=seed)
                else:
                    forecasts[target] = issue_forecast(observed, target=target, method=method,
                        issue_at_utc=issue, intervals=intervals, site_timezone=site.timezone)
            forecast_truth = tuple(TruthDisturbance(
                interval, forecasts["pv_available_kw"].values_kw[index],
                forecasts["critical_load_kw"].values_kw[index],
                forecasts["fixed_load_kw"].values_kw[index])
                for index, interval in enumerate(intervals))
            errors = [abs(forecasts[target].values_kw[index] - getattr(actual_future[index], target))
                      for target in TARGETS for index in range(len(intervals))]
            mae = sum(errors) / len(errors)
            training_end = max(item.training_end_utc for item in forecasts.values())
            solved = solve_schedule(site, forecast_truth, objective, seed=seed)
            if solved.schedule is None:
                outcomes.append(ForecastDecisionOutcome(method, issue, training_end, mae,
                                solved.status, None, oracle_value, None, solved.message))
                continue
            replay = simulate(site, actual_future, seed, solved.schedule)
            realized = recompute_objective(replay, actual_future, objective)
            regret = None if oracle_value is None else max(0.0, realized - oracle_value)
            outcomes.append(ForecastDecisionOutcome(method, issue, training_end, mae,
                            solved.status, realized, oracle_value, regret, None))
        except (ValueError, InfeasibleSchedule) as exc:
            outcomes.append(ForecastDecisionOutcome(method, issue, None, None, "unavailable",
                            None, oracle_value, None, str(exc)))
    return tuple(outcomes)
