"""Fixed-schedule stress replay never upgrades stress results to reliability."""

import unittest
from datetime import datetime, timezone

from energy_lab.core.assets import BatteryConfig, EVConfig, GridConfig, PVConfig, PumpConfig, SiteConfig
from energy_lab.core.time import TimeWindow, make_intervals
from energy_lab.simulation.engine import CandidateScheduleStep, TruthDisturbance
from energy_lab.uncertainty.calibration import score_commitment
from energy_lab.uncertainty.scenarios import StressSpec, apply_stress


class StressTests(unittest.TestCase):
    def test_ev_pump_and_temperature_stress_remain_explicit(self):
        intervals = make_intervals(datetime(2026, 1, 1, tzinfo=timezone.utc), 4, 15)
        window = TimeWindow(intervals[0].start, intervals[-1].end)
        site = SiteConfig("s", "Asia/Kolkata", GridConfig(20, 0), PVConfig(0),
                          evs=(EVConfig("ev", window, 1, 4),),
                          pumps=(PumpConfig("pump", window, 2, 0.25),))
        truth = tuple(TruthDisturbance(item, 0, 1, 1, outdoor_temperature_c=30)
                      for item in intervals)
        stressed_site, stressed_truth = apply_stress(site, truth,
            StressSpec("timing", ev_arrival_shift_intervals=1,
                       ev_departure_shift_intervals=-1, pump_runtime_factor=2,
                       outdoor_temperature_delta_c=2))
        self.assertEqual(stressed_site.evs[0].window.start, intervals[1].start)
        self.assertEqual(stressed_site.evs[0].window.end, intervals[-1].start)
        self.assertEqual(stressed_site.pumps[0].required_runtime_hours, 0.5)
        self.assertEqual(stressed_truth[0].outdoor_temperature_c, 32)
        with self.assertRaises(ValueError):
            StressSpec("invalid", ev_arrival_shift_intervals=1.5)

    def test_physical_failure_counts_and_confidence_is_unknown(self):
        intervals = make_intervals(datetime(2026, 1, 1, tzinfo=timezone.utc), 2, 15)
        site = SiteConfig("s", "Asia/Kolkata", GridConfig(100, 0), PVConfig(0),
                          BatteryConfig(20, 0.1, 0.9, 10, 5, 5, 1, 1))
        truth = tuple(TruthDisturbance(item, 0, 5, 5) for item in intervals)
        baseline = tuple(CandidateScheduleStep(item) for item in intervals)
        committed = (CandidateScheduleStep(intervals[0], battery_discharge_kw=5),
                     CandidateScheduleStep(intervals[1], battery_charge_kw=5))
        result = score_commitment(site, truth, baseline, committed,
                                  (StressSpec("normal"), StressSpec("low-soc", initial_battery_energy_kwh=2)),
                                  seed=1, promised_kw=5, direction="down", start_index=0,
                                  duration_intervals=1)
        self.assertEqual(result.sample_count, 2)
        self.assertEqual(result.success_count, 1)
        self.assertEqual(result.success_fraction, 0.5)
        self.assertIsNone(result.tested_reliable_kw)
        self.assertIsNone(result.wilson_lower_95)
        self.assertFalse(result.outcomes[1].success)
        derated = score_commitment(site, truth, baseline, committed,
                                   (StressSpec("derated", battery_discharge_factor=0.5),),
                                   seed=1, promised_kw=5, direction="down", start_index=0,
                                   duration_intervals=1)
        self.assertFalse(derated.outcomes[0].success)
        self.assertIn("battery power rating exceeded", derated.outcomes[0].failure_reason)

    def test_calibrated_label_requires_sampled_holdout(self):
        intervals = make_intervals(datetime(2026, 1, 1, tzinfo=timezone.utc), 1, 15)
        site = SiteConfig("s", "Asia/Kolkata", GridConfig(10, 0), PVConfig(0))
        truth = (TruthDisturbance(intervals[0], 0, 1, 1),)
        schedule = (CandidateScheduleStep(intervals[0]),)
        with self.assertRaises(ValueError):
            score_commitment(site, truth, schedule, schedule, (StressSpec("stress"),),
                             seed=1, promised_kw=0, direction="up", start_index=0,
                             duration_intervals=1, calibrated_holdout=True)


if __name__ == "__main__":
    unittest.main()
