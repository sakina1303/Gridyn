"""Synthetic sensitivity ordering cannot become a field sensor recommendation."""

import unittest
from datetime import datetime, timezone

from energy_lab.core.assets import BatteryConfig, GridConfig, PVConfig, SiteConfig
from energy_lab.core.time import make_intervals
from energy_lab.experiments.measurement_sensitivity import assess_measurement_sensitivity
from energy_lab.flexibility.envelope import assess_envelope
from energy_lab.simulation.baselines import build_baseline
from energy_lab.simulation.engine import TruthDisturbance


class MeasurementSensitivityTests(unittest.TestCase):
    def test_fixed_commitment_is_replayed_against_declared_bounds(self):
        intervals = make_intervals(datetime(2026, 1, 1, tzinfo=timezone.utc), 4, 15)
        site = SiteConfig("s", "Asia/Kolkata", GridConfig(100, 0), PVConfig(0),
                          BatteryConfig(20, .1, .9, 10, 5, 5, 1, 1))
        truth = tuple(TruthDisturbance(item, 0, 5, 5) for item in intervals)
        baseline = build_baseline(site, intervals, policy="B0")
        envelope = assess_envelope(site, truth, baseline.schedule, seed=7,
                                   start_index=0, duration_intervals=1, direction="down")
        promised = envelope.pass_for("operational").sustained_kw
        self.assertGreater(promised, 0)
        result = assess_measurement_sensitivity(
            site, truth, baseline.schedule, envelope.operational_schedule,
            seed=7, promised_kw=promised, direction="down",
            start_index=0, duration_intervals=1)
        self.assertEqual({item.measurement for item in result.candidates},
                         {"Critical and fixed load", "Battery state of charge",
                          "Battery discharge availability"})
        self.assertTrue(all(item.burden is None for item in result.candidates))
        self.assertIn("field priority unvalidated", result.limitation)
        self.assertTrue(all(item.scenario_count == 3 for item in result.candidates))

    def test_zero_response_cannot_be_ranked(self):
        intervals = make_intervals(datetime(2026, 1, 1, tzinfo=timezone.utc), 1, 15)
        site = SiteConfig("s", "Asia/Kolkata", GridConfig(100, 0), PVConfig(0))
        truth = (TruthDisturbance(intervals[0], 0, 5, 5),)
        baseline = build_baseline(site, intervals, policy="B0").schedule
        with self.assertRaises(ValueError):
            assess_measurement_sensitivity(site, truth, baseline, baseline,
                seed=7, promised_kw=0, direction="down", start_index=0, duration_intervals=1)


if __name__ == "__main__":
    unittest.main()
