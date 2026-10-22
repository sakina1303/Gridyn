"""Analytical joint-envelope cases and independent recovery replay."""

import unittest
from datetime import datetime, timezone

from energy_lab.core.assets import EVConfig, GridConfig, PVConfig, SiteConfig
from energy_lab.core.time import TimeWindow, make_intervals
from energy_lab.flexibility.envelope import assess_envelope
from energy_lab.simulation.baselines import build_baseline
from energy_lab.simulation.engine import CandidateScheduleStep, TruthDisturbance


class EnvelopeTests(unittest.TestCase):
    def setUp(self):
        self.intervals = make_intervals(datetime(2026, 1, 1, tzinfo=timezone.utc), 2, 15)
        self.truth = tuple(TruthDisturbance(interval, 0, 0, 0) for interval in self.intervals)

    def test_no_flexibility_has_zero_response(self):
        site = SiteConfig("s", "Asia/Kolkata", GridConfig(100, 0), PVConfig(0))
        truth = tuple(TruthDisturbance(interval, 0, 5, 5) for interval in self.intervals)
        schedule = tuple(CandidateScheduleStep(interval) for interval in self.intervals)
        for direction in ("up", "down"):
            result = assess_envelope(site, truth, schedule, seed=1, start_index=0,
                                     duration_intervals=1, direction=direction)
            self.assertEqual(result.pass_for("operational").status, "optimal")
            self.assertAlmostEqual(result.pass_for("operational").sustained_kw, 0)
            self.assertIsNone(result.reliable_kw)

    def test_single_ev_shift_and_recovery(self):
        window = TimeWindow(self.intervals[0].start, self.intervals[-1].end)
        site = SiteConfig("s", "Asia/Kolkata", GridConfig(100, 0), PVConfig(0),
                          evs=(EVConfig("ev", window, 5, 20),))
        baseline = build_baseline(site, self.intervals, policy="B0")
        result = assess_envelope(site, self.truth, baseline.schedule, seed=1,
                                 start_index=0, duration_intervals=1, direction="down")
        self.assertEqual(result.pass_for("operational").status, "optimal")
        self.assertAlmostEqual(result.pass_for("operational").sustained_kw, 20)
        self.assertAlmostEqual(result.recovery_import_delta_kwh, 5)
        self.assertAlmostEqual(result.operational_trajectory.steps[-1].services.ev_delivered_kwh[0][1], 5)

    def test_shared_grid_limit_prevents_nameplate_sum(self):
        window = TimeWindow(self.intervals[0].start, self.intervals[-1].end)
        site = SiteConfig("s", "Asia/Kolkata", GridConfig(20, 0), PVConfig(0),
                          evs=(EVConfig("a", window, 2.5, 20), EVConfig("b", window, 2.5, 20)))
        baseline = build_baseline(site, self.intervals, policy="B0")
        result = assess_envelope(site, self.truth, baseline.schedule, seed=1,
                                 start_index=1, duration_intervals=1, direction="up")
        self.assertEqual(result.pass_for("operational").status, "optimal")
        self.assertAlmostEqual(result.pass_for("operational").sustained_kw, 20)
        self.assertLess(result.pass_for("operational").sustained_kw, 40)


if __name__ == "__main__":
    unittest.main()
