"""Scenario strategies use the same changed site and hidden truth."""

import unittest
from datetime import datetime, timezone

from energy_lab.core.assets import EVConfig, GridConfig, PVConfig, SiteConfig
from energy_lab.core.time import TimeWindow, make_intervals
from energy_lab.optimization.objectives import ObjectiveConfig
from energy_lab.scenarios.runner import compare_scenario
from energy_lab.scenarios.schema import ScenarioConfig
from energy_lab.simulation.engine import TruthDisturbance


class ScenarioComparisonTests(unittest.TestCase):
    def test_b0_b1_and_optimizer_are_compared_on_one_scenario(self):
        intervals = make_intervals(datetime(2026, 1, 1, 4, tzinfo=timezone.utc), 8, 15)
        window = TimeWindow(intervals[0].start, intervals[-1].end)
        site = SiteConfig("campus", "Asia/Kolkata", GridConfig(100, 0), PVConfig(0),
                          evs=(EVConfig("ev", window, 2, 4),))
        truth = tuple(TruthDisturbance(interval, 0, 2, 10 if index < 2 else 2)
                      for index, interval in enumerate(intervals))
        result = compare_scenario(site, truth, "same-truth", ScenarioConfig("stress", "data", 20),
                                  objective=ObjectiveConfig("peak"))
        self.assertEqual(result.truth_sha256, "same-truth")
        self.assertEqual(result.baseline_status, "valid")
        self.assertEqual(result.rule_status, "valid")
        self.assertEqual(result.scenario_status, "optimal_validated")
        self.assertGreater(result.baseline_peak_kw, result.rule_peak_kw)
        self.assertLessEqual(result.scenario_peak_kw, result.rule_peak_kw + 1e-6)

    def test_infeasible_rule_does_not_hide_optimizer_result(self):
        intervals = make_intervals(datetime(2026, 1, 1, 4, tzinfo=timezone.utc), 8, 15)
        window = TimeWindow(intervals[0].start, intervals[-1].end)
        site = SiteConfig("campus", "Asia/Kolkata", GridConfig(100, 0), PVConfig(0),
                          evs=(EVConfig("ev", window, 2, 4),))
        truth = tuple(TruthDisturbance(interval, 0, 2, 10 if index < 2 else 2)
                      for index, interval in enumerate(intervals))
        result = compare_scenario(site, truth, "same-truth", ScenarioConfig("stress", "data", 13),
                                  objective=ObjectiveConfig("peak"))
        self.assertEqual(result.baseline_status, "infeasible")
        self.assertIsNone(result.baseline_peak_kw)
        self.assertEqual(result.rule_status, "valid")
        self.assertEqual(result.scenario_status, "optimal_validated")
        self.assertIsNone(result.peak_delta_kw)


if __name__ == "__main__":
    unittest.main()
