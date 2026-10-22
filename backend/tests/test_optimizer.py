"""Hand-priced MILP, infeasibility and independent replay rejection."""

import unittest
from datetime import datetime, timezone

from energy_lab.core.assets import BatteryConfig, EVConfig, GridConfig, HVACConfig, PVConfig, PumpConfig, SiteConfig
from energy_lab.core.time import TimeWindow, make_intervals
from energy_lab.optimization.objectives import ObjectiveConfig
from energy_lab.optimization.solve import solve_schedule
from energy_lab.optimization.validate import validate_schedule
from energy_lab.simulation.engine import CandidateScheduleStep, InfeasibleSchedule, TruthDisturbance


class OptimizerTests(unittest.TestCase):
    def setUp(self):
        self.intervals = make_intervals(datetime(2026, 1, 1, tzinfo=timezone.utc), 2, 15)

    def test_ev_uses_cheaper_interval_and_objective_recomputes(self):
        window = TimeWindow(self.intervals[0].start, self.intervals[-1].end)
        site = SiteConfig("s", "Asia/Kolkata", GridConfig(20, 0), PVConfig(0),
                          evs=(EVConfig("ev", window, 5, 20),))
        truth = tuple(TruthDisturbance(t, 0, 0, 0) for t in self.intervals)
        config = ObjectiveConfig("cost", (10, 1), (0, 0))
        run = solve_schedule(site, truth, config, seed=1)
        self.assertEqual(run.status, "optimal_validated", run.message)
        self.assertAlmostEqual(run.validation.recomputed_objective, 5)
        self.assertAlmostEqual(run.schedule[0].ev_power_kw["ev"], 0)
        self.assertAlmostEqual(run.schedule[1].ev_power_kw["ev"], 20)
        self.assertEqual(run.validation.maximum_balance_residual_kw, 0)

    def test_no_import_with_critical_load_is_infeasible(self):
        site = SiteConfig("s", "Asia/Kolkata", GridConfig(0, 0), PVConfig(0))
        truth = tuple(TruthDisturbance(t, 0, 1, 0) for t in self.intervals)
        run = solve_schedule(site, truth, ObjectiveConfig("peak"), seed=1)
        self.assertNotEqual(run.status, "optimal_validated")
        self.assertIsNone(run.schedule)

    def test_independent_checker_rejects_impossible_soc(self):
        site = SiteConfig("s", "Asia/Kolkata", GridConfig(20, 0), PVConfig(0),
                          BatteryConfig(10, 0.1, 0.9, 1, 5, 5, 1, 1))
        truth = tuple(TruthDisturbance(t, 0, 1, 0) for t in self.intervals)
        schedule = (CandidateScheduleStep(self.intervals[0], battery_discharge_kw=5),
                    CandidateScheduleStep(self.intervals[1], battery_charge_kw=5))
        with self.assertRaises(InfeasibleSchedule):
            validate_schedule(site, truth, 1, schedule, ObjectiveConfig("peak"))

    def test_full_day_joint_assets_replay(self):
        intervals = make_intervals(datetime(2026, 1, 1, tzinfo=timezone.utc), 96, 15)
        window = TimeWindow(intervals[20].start, intervals[60].end)
        site = SiteConfig("campus", "Asia/Kolkata", GridConfig(100, 10), PVConfig(20),
                          BatteryConfig(30, 0.1, 0.9, 15, 10, 10, 0.9, 0.9),
                          evs=(EVConfig("ev", window, 10, 10),),
                          pumps=(PumpConfig("pump", window, 3, 1, 2),),
                          hvacs=(HVACConfig("hvac", (window,), 2, 5),))
        truth = tuple(TruthDisturbance(interval, 10 if 24 <= index < 60 else 0, 5, 5)
                      for index, interval in enumerate(intervals))
        run = solve_schedule(site, truth, ObjectiveConfig("peak"), seed=7)
        self.assertEqual(run.status, "optimal_validated", run.message)
        self.assertEqual(len(run.schedule), 96)
        self.assertGreaterEqual(run.validation.trajectory.final_battery_energy_kwh, 15)
        self.assertGreaterEqual(run.validation.trajectory.steps[-1].services.ev_delivered_kwh[0][1], 10)
        self.assertGreaterEqual(run.validation.trajectory.steps[-1].services.pump_runtime_hours[0][1], 1)


if __name__ == "__main__":
    unittest.main()
