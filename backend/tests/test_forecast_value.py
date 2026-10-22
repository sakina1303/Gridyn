"""Forecast error and realized decision regret use the same optimizer/truth."""

import unittest
from datetime import datetime, timezone

from energy_lab.core.assets import BatteryConfig, GridConfig, PVConfig, SiteConfig
from energy_lab.experiments.forecast_value import compare_forecast_decisions
from energy_lab.optimization.objectives import ObjectiveConfig
from energy_lab.simulation.generator import GenerationConfig, generate_truth
from energy_lab.simulation.observer import ObservationConfig, ObservedRecord, observe_truth


class ForecastValueTests(unittest.TestCase):
    def test_future_observation_changes_do_not_change_issued_decision(self):
        site = SiteConfig("s", "Asia/Kolkata", GridConfig(250, 0), PVConfig(0),
                          BatteryConfig(20, 0.1, 0.9, 10, 5, 5, 0.9, 0.9))
        generated = generate_truth(GenerationConfig("truth", site,
            datetime(2026, 1, 1, tzinfo=timezone.utc), 9 * 96, 7))
        records = observe_truth(generated, ObservationConfig("observed", 8)).observed.records
        actual = generated.disturbances[8 * 96:8 * 96 + 2]
        issue = actual[0].interval.start
        first = compare_forecast_decisions(site, records, actual, issue_at_utc=issue,
            objective=ObjectiveConfig("peak"), seed=7, methods=("previous_day", "random_forest"))
        modified = tuple(item if item.interval.end <= issue else
                         ObservedRecord(item.interval, item.quantity, 999, item.unit) for item in records)
        second = compare_forecast_decisions(site, modified, actual, issue_at_utc=issue,
            objective=ObjectiveConfig("peak"), seed=7, methods=("previous_day", "random_forest"))
        self.assertEqual(first, second)
        self.assertTrue(all(item.training_end_utc == issue for item in first))
        self.assertTrue(all(item.oracle_objective is not None for item in first))


if __name__ == "__main__":
    unittest.main()
