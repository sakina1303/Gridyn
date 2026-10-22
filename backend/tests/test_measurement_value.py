"""Synthetic measurement comparisons retain abstention and unknown quantities."""

import unittest
from datetime import datetime, timezone

from energy_lab.experiments.ablations import AblationResult
from energy_lab.experiments.measurement_value import compare_restorations
from energy_lab.simulation.observer import ObservationConfig


class MeasurementValueTests(unittest.TestCase):
    def test_one_at_a_time_restoration_reports_enabled_assessment_without_fake_gain(self):
        full = ObservationConfig("full", 7)
        without_pv = ObservationConfig("without-pv", 7,
            visible_quantities=("critical_load_kw", "fixed_load_kw", "outdoor_temperature_c"))
        changed_resolution = ObservationConfig("coarse", 7, interval_minutes=30)
        issue = datetime(2026, 1, 2, tzinfo=timezone.utc)
        results = (
            AblationResult("full", "truth", "full-hash", issue, "delivered", None, 5, 5, 0),
            AblationResult("without-pv", "truth", "mask-hash", issue, "abstained", "PV absent", None, None, None),
            AblationResult("coarse", "truth", "coarse-hash", issue, "abstained", "coarse", None, None, None),
        )
        effects = compare_restorations((full, without_pv, changed_resolution), results)
        self.assertEqual(len(effects), 1)
        self.assertEqual(effects[0].quantity, "pv_available_kw")
        self.assertTrue(effects[0].assessment_enabled)
        self.assertIsNone(effects[0].overstatement_reduction_kw)
        self.assertIsNone(effects[0].interval_width_reduction_kw)

    def test_unpaired_truth_is_rejected(self):
        full = ObservationConfig("full", 7)
        masked = ObservationConfig("masked", 7,
            visible_quantities=("critical_load_kw", "fixed_load_kw", "outdoor_temperature_c"))
        issue = datetime(2026, 1, 2, tzinfo=timezone.utc)
        results = (
            AblationResult("full", "truth-a", "a", issue, "delivered", None, 5, 5, 0),
            AblationResult("masked", "truth-b", "b", issue, "abstained", None, None, None, None),
        )
        with self.assertRaises(ValueError):
            compare_restorations((full, masked), results)


if __name__ == "__main__":
    unittest.main()
