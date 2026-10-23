"""Stress-aware selection uses separate declared training and evaluation sets."""

import unittest
from datetime import datetime, timezone

from energy_lab.core.assets import GridConfig, PVConfig, SiteConfig
from energy_lab.core.time import make_intervals
from energy_lab.scenarios.schema import ScenarioConfig
from energy_lab.scenarios.stress_aware import select_stress_aware_schedule
from energy_lab.simulation.engine import TruthDisturbance
from energy_lab.uncertainty.scenarios import StressSpec


class StressAwareTests(unittest.TestCase):
    def setUp(self):
        intervals = make_intervals(datetime(2026, 1, 1, tzinfo=timezone.utc), 4, 15)
        self.site = SiteConfig("s", "Asia/Kolkata", GridConfig(30, 0), PVConfig(0))
        self.truth = tuple(TruthDisturbance(item, 0, 5, 5) for item in intervals)
        self.training = (StressSpec("train-normal"), StressSpec("train-high", fixed_load_factor=1.1))
        self.evaluation = (StressSpec("eval-higher", fixed_load_factor=1.2),)

    def test_selected_schedule_replays_on_separate_evaluation(self):
        outcome = select_stress_aware_schedule(
            self.site, self.truth, ScenarioConfig("s", "d", grid_import_limit_kw=20),
            self.training, self.evaluation)
        self.assertEqual(outcome.status, "selected")
        self.assertEqual(len(outcome.training), 2)
        self.assertEqual(len(outcome.evaluation), 1)
        self.assertEqual(outcome.evaluation[0].status, "valid")
        self.assertAlmostEqual(outcome.evaluation[0].peak_import_kw, 11)
        self.assertIn("unknown", outcome.evidence_label)

    def test_no_candidate_is_explicit_when_training_stress_breaks_grid_limit(self):
        outcome = select_stress_aware_schedule(
            self.site, self.truth, ScenarioConfig("s", "d", grid_import_limit_kw=10),
            self.training, self.evaluation)
        self.assertEqual(outcome.status, "no_validated_candidate")
        self.assertIsNone(outcome.reference_peak_kw)
        self.assertEqual(outcome.evaluation, ())

    def test_training_evaluation_ids_cannot_overlap(self):
        with self.assertRaises(ValueError):
            select_stress_aware_schedule(
                self.site, self.truth, ScenarioConfig("s", "d"),
                (StressSpec("same"),), (StressSpec("same"),))


if __name__ == "__main__":
    unittest.main()
