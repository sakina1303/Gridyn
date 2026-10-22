import random
import unittest
from datetime import datetime, timezone

from energy_lab.core.assets import BatteryConfig, EVConfig, GridConfig, HVACConfig, PVConfig, PumpConfig, SiteConfig
from energy_lab.core.flows import PhysicalInfeasibility, settle_flows
from energy_lab.core.time import TimeInterval, TimeWindow, local_to_utc, make_intervals, utc_to_local, validate_contiguous
from energy_lab.core.units import (
    EnergyKWh, IntervalDuration, PowerKW, average_power_from_energy,
    balance_tolerance_kw, energy_from_power, parse_energy, parse_power,
)


START = datetime(2026, 1, 1, tzinfo=timezone.utc)


class UnitAndTimeTests(unittest.TestCase):
    def test_power_energy_and_parsing(self):
        for minutes in (15, 30, 60):
            duration = IntervalDuration(minutes)
            powers = [1.0, 7.5, 100.0]
            total = sum(energy_from_power(PowerKW(p), duration).value for p in powers)
            self.assertAlmostEqual(total, sum(p * minutes / 60 for p in powers))
            for power in powers:
                energy = energy_from_power(PowerKW(power), duration)
                self.assertAlmostEqual(average_power_from_energy(energy, duration).value, power)
        self.assertEqual(parse_power(1000, "W"), PowerKW(1))
        self.assertEqual(parse_power(1, "MW"), PowerKW(1000))
        self.assertEqual(parse_energy(1000, "Wh"), EnergyKWh(1))
        with self.assertRaises(ValueError):
            parse_power(1, "kWh")
        with self.assertRaises(ValueError):
            IntervalDuration(10)

    def test_utc_half_open_and_resolutions(self):
        for minutes in (15, 30, 60):
            intervals = make_intervals(START, 4, minutes)
            validate_contiguous(intervals, required_minutes=minutes)
            self.assertEqual(intervals[0].end, intervals[1].start)
            self.assertFalse(intervals[0].overlaps(intervals[1]))
            self.assertTrue(TimeWindow(intervals[0].start, intervals[-1].end).contains(intervals[1]))
        with self.assertRaises(ValueError):
            TimeInterval(START, START)
        with self.assertRaises(ValueError):
            make_intervals(datetime(2026, 1, 1), 1, 15)
        with self.assertRaises(ValueError):
            make_intervals(START, 1.0, 15)

    def test_timezone_and_dst(self):
        local = datetime(2026, 1, 1, 5, 30)
        utc = local_to_utc(local, "Asia/Kolkata")
        self.assertEqual(utc, START)
        self.assertEqual(utc_to_local(utc, "Asia/Kolkata").replace(tzinfo=None), local)
        with self.assertRaisesRegex(ValueError, "nonexistent"):
            local_to_utc(datetime(2026, 3, 8, 2, 30), "America/New_York")
        with self.assertRaisesRegex(ValueError, "ambiguous"):
            local_to_utc(datetime(2026, 11, 1, 1, 30), "America/New_York")
        self.assertNotEqual(
            local_to_utc(datetime(2026, 11, 1, 1, 30), "America/New_York", fold=0),
            local_to_utc(datetime(2026, 11, 1, 1, 30), "America/New_York", fold=1),
        )


class AssetAndFlowTests(unittest.TestCase):
    def test_invalid_assets(self):
        window = TimeWindow(START, make_intervals(START, 1, 15)[0].end)
        with self.assertRaises(ValueError):
            GridConfig(-1, 0)
        with self.assertRaises(ValueError):
            BatteryConfig(10, 0.9, 0.2, 5, 2, 2, 0.9, 0.9)
        with self.assertRaisesRegex(ValueError, "carryover"):
            BatteryConfig(10, 0, 1, 5, 2, 2, 0.9, 0.9, min_terminal_energy_kwh=4)
        with self.assertRaises(ValueError):
            EVConfig("ev", window, 1, -2)
        with self.assertRaises(ValueError):
            PumpConfig("pump", window, 2, 0.25, 0)
        with self.assertRaises(ValueError):
            HVACConfig("hvac", (window,), 10, 5)
        with self.assertRaises(ValueError):
            SiteConfig("s", "Asia/Kolkata", GridConfig(10, 0), PVConfig(0), evs=(EVConfig("x", window, 0, 1),), pumps=(PumpConfig("x", window, 1, 0),))

    def test_hand_balance_and_signs(self):
        flows = settle_flows(
            pv_available_kw=10, critical_load_kw=5, fixed_load_kw=8,
            flexible_load_kw=2, battery_charge_kw=0, battery_discharge_kw=0,
            grid=GridConfig(20, 0), pv=PVConfig(10),
        )
        self.assertEqual(flows.grid_import_kw, 5)
        self.assertEqual(flows.net_grid_kw, 5)
        self.assertEqual(flows.balance_residual_kw, 0)
        export = settle_flows(
            pv_available_kw=20, critical_load_kw=5, fixed_load_kw=0,
            flexible_load_kw=0, battery_charge_kw=0, battery_discharge_kw=0,
            grid=GridConfig(20, 8), pv=PVConfig(20),
        )
        self.assertEqual((export.grid_export_kw, export.pv_curtailment_kw, export.net_grid_kw), (8, 7, -8))

    def test_property_balance_and_limits(self):
        rng = random.Random(713)
        grid = GridConfig(500, 500)
        pv = PVConfig(100)
        for _ in range(250):
            solar = rng.uniform(0, 100)
            critical = rng.uniform(0, 40)
            fixed = rng.uniform(0, 100)
            flexible = rng.uniform(0, 40)
            charge = rng.uniform(0, 30) if rng.random() < 0.5 else 0.0
            discharge = 0.0 if charge else rng.uniform(0, 30)
            flows = settle_flows(
                pv_available_kw=solar, critical_load_kw=critical, fixed_load_kw=fixed,
                flexible_load_kw=flexible, battery_charge_kw=charge, battery_discharge_kw=discharge,
                grid=grid, pv=pv,
            )
            self.assertLessEqual(abs(flows.balance_residual_kw), balance_tolerance_kw(500))
            self.assertGreaterEqual(flows.grid_import_kw, 0)
            self.assertGreaterEqual(flows.grid_export_kw, 0)
            self.assertLessEqual(flows.pv_curtailment_kw, flows.pv_available_kw)
            self.assertFalse(flows.grid_import_kw and flows.grid_export_kw)

    def test_no_grid_import_and_no_curtailment_fail(self):
        with self.assertRaises(PhysicalInfeasibility):
            settle_flows(pv_available_kw=0, critical_load_kw=1, fixed_load_kw=0,
                         flexible_load_kw=0, battery_charge_kw=0, battery_discharge_kw=0,
                         grid=GridConfig(0, 0), pv=PVConfig(0))
        with self.assertRaises(PhysicalInfeasibility):
            settle_flows(pv_available_kw=10, critical_load_kw=0, fixed_load_kw=0,
                         flexible_load_kw=0, battery_charge_kw=0, battery_discharge_kw=0,
                         grid=GridConfig(0, 0), pv=PVConfig(10, allow_curtailment=False))
        supplied = settle_flows(pv_available_kw=5, critical_load_kw=5, fixed_load_kw=0,
                                flexible_load_kw=0, battery_charge_kw=0, battery_discharge_kw=0,
                                grid=GridConfig(0, 0), pv=PVConfig(5, allow_curtailment=False))
        self.assertEqual((supplied.grid_import_kw, supplied.pv_curtailment_kw), (0, 0))
        with self.assertRaisesRegex(PhysicalInfeasibility, "battery surplus"):
            settle_flows(pv_available_kw=0, critical_load_kw=0, fixed_load_kw=0,
                         flexible_load_kw=0, battery_charge_kw=0, battery_discharge_kw=5,
                         grid=GridConfig(0, 0), pv=PVConfig(0))
