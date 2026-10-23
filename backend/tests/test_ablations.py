"""Paired truth, issue-time isolation and explicit abstention outcomes."""

import unittest
from datetime import datetime, timezone

from energy_lab.core.assets import BatteryConfig, GridConfig, PVConfig, SiteConfig
from energy_lab.experiments.ablations import run_paired_ablation
from energy_lab.simulation.generator import GenerationConfig, generate_truth
from energy_lab.simulation.observer import ObservationConfig


class AblationTests(unittest.TestCase):
    def test_paired_missingness_and_resolution_keep_truth_fixed(self):
        site = SiteConfig("s", "Asia/Kolkata", GridConfig(100, 0), PVConfig(0),
                          BatteryConfig(20, 0.1, 0.9, 10, 5, 5, 1, 1))
        start = datetime(2026, 1, 1, tzinfo=timezone.utc)
        generated = generate_truth(GenerationConfig("truth", site, start, 192, 7,
                                                     critical_base_kw=5, fixed_base_kw=5,
                                                     day_activity_kw=0, evening_activity_kw=0,
                                                     cooling_kw_per_c_above_28=0))
        cases = (
            ObservationConfig("clean", 11),
            ObservationConfig("missing", 11, missing_blocks=((0, 1),)),
            ObservationConfig("coarse", 11, interval_minutes=30),
        )
        results = run_paired_ablation(generated, cases, issue_at_utc=generated.disturbances[96].interval.start,
                                      horizon_intervals=96, start_index=0, duration_intervals=1,
                                      direction="down", seed=7)
        self.assertEqual({row.truth_sha256 for row in results}, {generated.manifest.truth_sha256})
        self.assertEqual(results[0].status, "delivered")
        self.assertGreater(results[0].estimated_sustained_kw, 0)
        self.assertEqual(results[1].status, "abstained")
        self.assertEqual(results[2].status, "abstained")
        self.assertIsNone(results[1].estimated_sustained_kw)

    def test_invalid_forecast_physics_becomes_abstention(self):
        site = SiteConfig("s", "Asia/Kolkata", GridConfig(100, 0), PVConfig(0))
        generated = generate_truth(GenerationConfig(
            "truth", site, datetime(2026, 1, 1, tzinfo=timezone.utc), 192, 7,
            critical_base_kw=5, fixed_base_kw=5, day_activity_kw=0,
            evening_activity_kw=0, cooling_kw_per_c_above_28=0))
        result = run_paired_ablation(
            generated, (ObservationConfig("negative-observation", 7, power_bias_fraction=-2),),
            issue_at_utc=generated.disturbances[96].interval.start,
            horizon_intervals=96, start_index=0, duration_intervals=1,
            direction="down", seed=7)[0]
        self.assertEqual(result.status, "abstained")
        self.assertIsNone(result.estimated_sustained_kw)


if __name__ == "__main__":
    unittest.main()
