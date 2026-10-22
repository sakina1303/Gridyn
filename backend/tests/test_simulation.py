import random
import unittest
from datetime import datetime, timezone

from energy_lab.core.assets import BatteryConfig, EVConfig, GridConfig, HVACConfig, PVConfig, PumpConfig, SiteConfig
from energy_lab.core.time import TimeWindow, make_intervals
from energy_lab.core.units import IntervalDuration, balance_tolerance_kw
from energy_lab.simulation.battery import BatteryState, transition_battery
from energy_lab.simulation.engine import CandidateScheduleStep, InfeasibleSchedule, TruthDisturbance, simulate


START = datetime(2026, 1, 1, tzinfo=timezone.utc)


def fixture(count=4, *, pv=0, critical=0, fixed=0, tariff=0):
    intervals = make_intervals(START, count, 15)
    truth = tuple(TruthDisturbance(i, pv, critical, fixed, tariff_inr_per_kwh=tariff) for i in intervals)
    actions = tuple(CandidateScheduleStep(i) for i in intervals)
    return intervals, truth, actions


def battery(initial=10, min_fraction=0, max_fraction=1, capacity=20, rate=10, efficiency=1, terminal=None):
    return BatteryConfig(capacity, min_fraction, max_fraction, initial, rate, rate,
                         efficiency, efficiency, min_terminal_energy_kwh=terminal)


class SimulationTests(unittest.TestCase):
    def test_no_battery_no_solar_no_flexibility_and_energy(self):
        _, truth, actions = fixture(4, critical=5, fixed=3)
        site = SiteConfig("s", "Asia/Kolkata", GridConfig(20, 0), PVConfig(0))
        result = simulate(site, truth, 1, actions)
        self.assertEqual(result.grid_import_kwh, 8)
        self.assertIsNone(result.final_battery_energy_kwh)
        for step in result.steps:
            self.assertEqual(step.flows.grid_import_kw, 8)
            self.assertEqual(step.flows.pv_available_kw, 0)
            self.assertEqual(step.flows.flexible_load_kw, 0)
            self.assertEqual(step.critical_served_kw, 5)

    def test_no_grid_import_preserves_critical_load(self):
        _, truth, actions = fixture(4, critical=5)
        site = SiteConfig("s", "Asia/Kolkata", GridConfig(0, 0), PVConfig(0))
        with self.assertRaisesRegex(InfeasibleSchedule, "critical"):
            simulate(site, truth, 1, actions)

    def test_no_curtailment_rejects_surplus(self):
        _, truth, actions = fixture(4, pv=10)
        site = SiteConfig("s", "Asia/Kolkata", GridConfig(0, 0), PVConfig(10, False))
        with self.assertRaisesRegex(InfeasibleSchedule, "curtailed"):
            simulate(site, truth, 1, actions)

    def test_battery_at_max_and_min_soc(self):
        intervals, truth, _ = fixture(4)
        max_site = SiteConfig("s", "Asia/Kolkata", GridConfig(20, 20), PVConfig(0), battery=battery(initial=20))
        charge = (CandidateScheduleStep(intervals[0], battery_charge_kw=1),) + tuple(CandidateScheduleStep(i) for i in intervals[1:])
        with self.assertRaisesRegex(InfeasibleSchedule, "SOC"):
            simulate(max_site, truth, 1, charge)
        min_site = SiteConfig("s", "Asia/Kolkata", GridConfig(20, 20), PVConfig(0), battery=battery(initial=0))
        discharge = (CandidateScheduleStep(intervals[0], battery_discharge_kw=1),) + tuple(CandidateScheduleStep(i) for i in intervals[1:])
        with self.assertRaisesRegex(InfeasibleSchedule, "SOC"):
            simulate(min_site, truth, 1, discharge)

    def test_battery_efficiency_hand_case_and_no_simultaneous_power(self):
        config = battery(initial=10, capacity=30, efficiency=0.9)
        state = BatteryState(10)
        for _ in range(4):
            state = transition_battery(config, state, charge_kw=10, discharge_kw=0, duration=IntervalDuration(15))
        self.assertAlmostEqual(state.energy_kwh, 19)
        for _ in range(4):
            state = transition_battery(config, state, charge_kw=0, discharge_kw=9, duration=IntervalDuration(15))
        self.assertAlmostEqual(state.energy_kwh, 9)
        with self.assertRaisesRegex(ValueError, "simultaneous"):
            transition_battery(config, state, charge_kw=1, discharge_kw=1, duration=IntervalDuration(15))

    def test_single_ev_service_window(self):
        intervals, truth, _ = fixture(8)
        window = TimeWindow(intervals[0].start, intervals[-1].end)
        ev = EVConfig("ev", window, required_energy_kwh=20, max_power_kw=20)
        site = SiteConfig("s", "Asia/Kolkata", GridConfig(30, 0), PVConfig(0), evs=(ev,))
        good = tuple(CandidateScheduleStep(i, ev_power_kw={"ev": 20 if n < 4 else 0}) for n, i in enumerate(intervals))
        result = simulate(site, truth, 1, good)
        self.assertAlmostEqual(result.steps[-1].services.ev_delivered_kwh[0][1], 20)
        self.assertAlmostEqual(result.grid_import_kwh, 20)
        bad = tuple(CandidateScheduleStep(i, ev_power_kw={"ev": 10 if n < 4 else 0}) for n, i in enumerate(intervals))
        with self.assertRaisesRegex(InfeasibleSchedule, "EV ev departure energy"):
            simulate(site, truth, 1, bad)

    def test_pump_service_and_minimum_run(self):
        intervals, truth, _ = fixture(4)
        pump = PumpConfig("pump", TimeWindow(intervals[0].start, intervals[-1].end), 20, 0.5, minimum_run_intervals=2)
        site = SiteConfig("s", "Asia/Kolkata", GridConfig(30, 0), PVConfig(0), pumps=(pump,))
        good = tuple(CandidateScheduleStep(i, pump_on={"pump": n in (0, 1)}) for n, i in enumerate(intervals))
        result = simulate(site, truth, 1, good)
        self.assertAlmostEqual(result.steps[-1].services.pump_runtime_hours[0][1], 0.5)
        bad = tuple(CandidateScheduleStep(i, pump_on={"pump": n in (0, 2)}) for n, i in enumerate(intervals))
        with self.assertRaisesRegex(InfeasibleSchedule, "minimum run"):
            simulate(site, truth, 1, bad)

    def test_hvac_conservative_bounds(self):
        intervals, truth, _ = fixture(4)
        hvac = HVACConfig("cool", (TimeWindow(intervals[0].start, intervals[-1].end),), 5, 10)
        site = SiteConfig("s", "Asia/Kolkata", GridConfig(20, 0), PVConfig(0), hvacs=(hvac,))
        good = tuple(CandidateScheduleStep(i, hvac_power_kw={"cool": 5}) for i in intervals)
        self.assertAlmostEqual(simulate(site, truth, 1, good).grid_import_kwh, 5)
        bad = tuple(CandidateScheduleStep(i, hvac_power_kw={"cool": 0}) for i in intervals)
        with self.assertRaisesRegex(InfeasibleSchedule, "HVAC"):
            simulate(site, truth, 1, bad)

    def test_multiple_interacting_assets_and_grid_limit(self):
        intervals, truth, _ = fixture(4, critical=10)
        window = TimeWindow(intervals[0].start, intervals[-1].end)
        site = SiteConfig("s", "Asia/Kolkata", GridConfig(30, 0), PVConfig(0),
                          battery=battery(initial=10, capacity=30, rate=10),
                          evs=(EVConfig("ev", window, 5, 10),),
                          pumps=(PumpConfig("pump", window, 20, 0.25),))
        actions = tuple(CandidateScheduleStep(i, battery_charge_kw=10 if n == 0 else 0,
                                             ev_power_kw={"ev": 10 if n in (0, 1) else 0},
                                             pump_on={"pump": n == 0}) for n, i in enumerate(intervals))
        with self.assertRaisesRegex(InfeasibleSchedule, "grid import limit"):
            simulate(site, truth, 1, actions)
        feasible_site = SiteConfig("s", "Asia/Kolkata", GridConfig(50, 0), PVConfig(0),
                                   battery=battery(initial=10, capacity=30, rate=10),
                                   evs=(EVConfig("ev", window, 5, 10),),
                                   pumps=(PumpConfig("pump", window, 20, 0.25),))
        valid = simulate(feasible_site, truth, 1, actions)
        self.assertEqual(valid.steps[0].flows.grid_import_kw, 50)
        self.assertAlmostEqual(valid.steps[-1].services.ev_delivered_kwh[0][1], 5)
        self.assertAlmostEqual(valid.steps[-1].services.pump_runtime_hours[0][1], 0.25)

    def test_pv_curtailment_hand_case(self):
        intervals, truth, _ = fixture(4, pv=100, critical=40)
        window = TimeWindow(intervals[0].start, intervals[-1].end)
        site = SiteConfig("s", "Asia/Kolkata", GridConfig(100, 0), PVConfig(100),
                          battery=battery(initial=0, capacity=100, rate=20),
                          evs=(EVConfig("ev", window, 10, 10),))
        actions = tuple(CandidateScheduleStep(i, battery_charge_kw=20, ev_power_kw={"ev": 10}) for i in intervals)
        result = simulate(site, truth, 1, actions)
        for step in result.steps:
            self.assertEqual(step.flows.pv_curtailment_kw, 30)
            self.assertAlmostEqual(step.flows.balance_residual_kw, 0)
        self.assertEqual(result.pv_curtailment_kwh, 30)

    def test_terminal_soc_prevents_free_initial_energy(self):
        intervals, truth, _ = fixture(4, critical=5)
        site = SiteConfig("s", "Asia/Kolkata", GridConfig(20, 0), PVConfig(0), battery=battery(initial=10))
        actions = tuple(CandidateScheduleStep(i, battery_discharge_kw=5) for i in intervals)
        with self.assertRaisesRegex(InfeasibleSchedule, "terminal"):
            simulate(site, truth, 1, actions)

    def test_property_battery_soc_transition(self):
        rng = random.Random(991)
        for _ in range(100):
            initial = rng.uniform(5, 15)
            config = battery(initial=initial, capacity=20, rate=10, efficiency=0.9)
            power = rng.uniform(0, 5)
            charging = rng.random() < 0.5
            charge, discharge = (power, 0) if charging else (0, power)
            result = transition_battery(config, BatteryState(initial), charge_kw=charge,
                                        discharge_kw=discharge, duration=IntervalDuration(15))
            expected = initial + 0.9 * charge * 0.25 - discharge * 0.25 / 0.9
            self.assertAlmostEqual(result.energy_kwh, expected)
            self.assertGreaterEqual(result.energy_kwh, config.min_energy_kwh)
            self.assertLessEqual(result.energy_kwh, config.max_energy_kwh)

    def test_tariff_does_not_change_physics(self):
        _, truth_a, actions = fixture(4, pv=2, critical=5, tariff=0)
        _, truth_b, _ = fixture(4, pv=2, critical=5, tariff=999)
        site = SiteConfig("s", "Asia/Kolkata", GridConfig(20, 0), PVConfig(2))
        a = simulate(site, truth_a, 1, actions)
        b = simulate(site, truth_b, 1, actions)
        self.assertEqual(tuple(x.flows for x in a.steps), tuple(x.flows for x in b.steps))

    def test_seeded_property_replay_balance_and_bounds(self):
        rng = random.Random(41)
        intervals = make_intervals(START, 96, 15)
        truth = tuple(TruthDisturbance(i, rng.uniform(0, 20), rng.uniform(1, 10), rng.uniform(0, 10)) for i in intervals)
        schedule = tuple(CandidateScheduleStep(i) for i in intervals)
        site = SiteConfig("s", "Asia/Kolkata", GridConfig(30, 20), PVConfig(20))
        first = simulate(site, truth, 41, schedule)
        second = simulate(site, truth, 41, schedule)
        self.assertEqual(first, second)
        for step in first.steps:
            self.assertLessEqual(abs(step.flows.balance_residual_kw), balance_tolerance_kw(30))
            self.assertLessEqual(step.flows.grid_import_kw, 30)
            self.assertEqual(step.critical_served_kw, step.flows.critical_load_kw)
