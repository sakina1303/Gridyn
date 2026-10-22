"""B0/B1 use static information and pass the independent physical replay."""

import unittest
from datetime import datetime, timezone

from energy_lab.core.assets import BatteryConfig, EVConfig, GridConfig, HVACConfig, PVConfig, PumpConfig, SiteConfig
from energy_lab.core.time import TimeWindow, make_intervals
from energy_lab.simulation.baselines import build_baseline, evaluate_baseline
from energy_lab.simulation.engine import InfeasibleSchedule, TruthDisturbance


class BaselineTests(unittest.TestCase):
    def setUp(self):
        self.intervals = make_intervals(datetime(2026, 1, 1, 4, 0, tzinfo=timezone.utc), 8, 15)
        window = TimeWindow(self.intervals[0].start, self.intervals[-1].end)
        self.site = SiteConfig(
            "campus", "Asia/Kolkata", GridConfig(100, 100), PVConfig(10),
            BatteryConfig(20, 0.1, 0.9, 10, 5, 5, 0.9, 0.9),
            evs=(EVConfig("ev", window, 2, 4),),
            pumps=(PumpConfig("pump", window, 3, 0.5, minimum_run_intervals=2),),
            hvacs=(HVACConfig("hvac", (window,), 1, 4),),
        )

    def test_both_baselines_serve_assets_and_keep_battery_idle(self):
        truth = tuple(TruthDisturbance(t, 2, 5, 5) for t in self.intervals)
        for label in ("B0", "B1"):
            plan, trajectory = evaluate_baseline(self.site, truth, seed=7, policy=label)
            self.assertEqual(len(trajectory.steps), 8)
            self.assertEqual(trajectory.final_battery_energy_kwh, 10)
            self.assertTrue(all(step.flows.balance_residual_kw == 0 for step in trajectory.steps))
            self.assertTrue(all(action.battery_charge_kw == action.battery_discharge_kw == 0 for action in plan.schedule))
            self.assertGreaterEqual(trajectory.steps[-1].services.ev_delivered_kwh[0][1], 2)
            self.assertGreaterEqual(trajectory.steps[-1].services.pump_runtime_hours[0][1], 0.5)

    def test_rule_uses_calendar_not_future_pv_or_load(self):
        b0 = build_baseline(self.site, self.intervals, policy="B0")
        b1 = build_baseline(self.site, self.intervals, policy="B1")
        self.assertEqual(b0.schedule[0].ev_power_kw["ev"], 4)
        self.assertEqual(b1.schedule[2].ev_power_kw["ev"], 4)
        low = tuple(TruthDisturbance(t, 0, 1, 1) for t in self.intervals)
        high = tuple(TruthDisturbance(t, 10, 10, 10) for t in self.intervals)
        self.assertEqual(evaluate_baseline(self.site, low, seed=1, policy="B1")[0].schedule,
                         evaluate_baseline(self.site, high, seed=1, policy="B1")[0].schedule)

    def test_impossible_service_is_reported(self):
        window = TimeWindow(self.intervals[0].start, self.intervals[1].end)
        site = SiteConfig("s", "Asia/Kolkata", GridConfig(100, 0), PVConfig(0),
                          evs=(EVConfig("ev", window, 5, 4),))
        with self.assertRaises(InfeasibleSchedule):
            build_baseline(site, self.intervals, policy="B0")


if __name__ == "__main__":
    unittest.main()
