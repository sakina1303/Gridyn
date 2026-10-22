import unittest
from dataclasses import replace
from datetime import datetime, timezone

from energy_lab.core.assets import GridConfig, PVConfig, SiteConfig
from energy_lab.core.units import IntervalDuration, PowerKW, energy_from_power
from energy_lab.simulation.generator import EVBehavior, GenerationConfig, generate_truth
from energy_lab.simulation.observer import ObservationConfig, observe_truth


START = datetime(2026, 1, 1, 18, 30, tzinfo=timezone.utc)  # local midnight in India


def config(seed=17, *, days=2, ev=False):
    site = SiteConfig("synthetic-campus", "Asia/Kolkata", GridConfig(250, 50), PVConfig(100))
    behavior = EVBehavior(2, 10, 8, 25) if ev else None
    return GenerationConfig("truth-1", site, START, 96 * days, seed, ev_behavior=behavior)


class GeneratorObserverTests(unittest.TestCase):
    def test_truth_reproducible_and_bounded(self):
        generated = generate_truth(config())
        rerun = generate_truth(config())
        self.assertEqual(generated, rerun)
        self.assertEqual(generated.manifest.truth_sha256, rerun.manifest.truth_sha256)
        self.assertNotEqual(generated.manifest.truth_sha256, generate_truth(config(18)).manifest.truth_sha256)
        self.assertEqual(len(generated.disturbances), 192)
        for item in generated.disturbances:
            self.assertGreaterEqual(item.pv_available_kw, 0)
            self.assertLessEqual(item.pv_available_kw, 100)
            self.assertGreaterEqual(item.critical_load_kw, 0)
            self.assertGreaterEqual(item.fixed_load_kw, 0)
            local_hour = item.interval.start.astimezone(__import__("zoneinfo").ZoneInfo("Asia/Kolkata")).hour
            if local_hour < 6 or local_hour >= 18:
                self.assertEqual(item.pv_available_kw, 0)
        self.assertTrue(any(item.pv_available_kw > 0 for item in generated.disturbances))

    def test_ev_stream_does_not_change_exogenous_truth(self):
        without = generate_truth(config(ev=False))
        with_evs = generate_truth(config(ev=True))
        self.assertEqual(without.disturbances, with_evs.disturbances)
        self.assertEqual(len(with_evs.site.evs), 4)
        self.assertEqual(len({ev.asset_id for ev in with_evs.site.evs}), 4)
        for ev in with_evs.site.evs:
            available_h = (ev.window.end - ev.window.start).total_seconds() / 3600
            self.assertLessEqual(ev.required_energy_kwh, ev.max_power_kw * available_h * ev.charger_efficiency)

    def test_30_and_60_min_aggregation_conserve_energy(self):
        truth = generate_truth(config(days=1))
        truth_energy = sum(energy_from_power(PowerKW(x.pv_available_kw), x.interval.duration).value for x in truth.disturbances)
        for minutes in (30, 60):
            observed = observe_truth(truth, ObservationConfig(f"observed-{minutes}", 99, interval_minutes=minutes,
                                                              visible_quantities=("pv_available_kw",))).observed
            observed_energy = sum(energy_from_power(PowerKW(x.value), x.interval.duration).value for x in observed.records)
            self.assertAlmostEqual(truth_energy, observed_energy)
            self.assertEqual(len(observed.records), 96 * 15 // minutes)
            self.assertEqual(observed.manifest.interval_minutes, minutes)

    def test_missing_noise_outlier_duplicate_and_timestamp_are_separate(self):
        truth = generate_truth(config(days=1))
        original_hash = truth.manifest.truth_sha256
        obs_config = ObservationConfig(
            "observed-corrupt", 9, interval_minutes=30,
            visible_quantities=("pv_available_kw",), missing_blocks=((2, 3),),
            power_noise_std_kw=1.0, power_bias_fraction=0.02,
            outlier_probability=1.0, outlier_multiplier=2.0,
            timestamp_shift_minutes=5, duplicate_indices=(0,),
        )
        first = observe_truth(truth, obs_config)
        second = observe_truth(truth, obs_config)
        self.assertEqual(first, second)
        self.assertEqual(truth.manifest.truth_sha256, original_hash)
        self.assertEqual(first.observed.manifest.truth_sha256, original_hash)
        self.assertNotEqual(first.observed.manifest.dataset_id, truth.manifest.dataset_id)
        self.assertEqual(len(first.hidden_corruption.missing), 3)
        self.assertEqual(len(first.hidden_corruption.duplicates), 1)
        self.assertEqual(len(first.observed.records), 48 - 3 + 1)
        self.assertEqual(first.observed.records[0].interval.start.minute, 35)
        self.assertNotIn("hidden_corruption", first.observed.__dataclass_fields__)

    def test_independent_observation_seed_changes_only_observations(self):
        truth = generate_truth(config(days=1))
        a = observe_truth(truth, ObservationConfig("obs-a", 1, power_noise_std_kw=1,
                                                  visible_quantities=("fixed_load_kw",)))
        b = observe_truth(truth, ObservationConfig("obs-b", 2, power_noise_std_kw=1,
                                                  visible_quantities=("fixed_load_kw",)))
        self.assertNotEqual(a.observed.manifest.observed_sha256, b.observed.manifest.observed_sha256)
        self.assertEqual(a.observed.manifest.truth_sha256, b.observed.manifest.truth_sha256)

    def test_invalid_observation_configuration_is_rejected(self):
        truth = generate_truth(config(days=1))
        with self.assertRaises(ValueError):
            observe_truth(truth, ObservationConfig("truth-1", 2))
        with self.assertRaises(ValueError):
            observe_truth(truth, ObservationConfig("obs", 2, missing_blocks=((95, 2),)))
        with self.assertRaises(ValueError):
            ObservationConfig("obs", 2, missing_probability=1.1)

    def test_truth_scenario_config_is_in_manifest(self):
        clear = generate_truth(config(days=1))
        cloudy = generate_truth(replace(config(days=1), weather_scenario="cloudy"))
        self.assertNotEqual(clear.manifest.config_sha256, cloudy.manifest.config_sha256)
        self.assertNotEqual(clear.manifest.truth_sha256, cloudy.manifest.truth_sha256)
        self.assertTrue(clear.manifest.synthetic)
