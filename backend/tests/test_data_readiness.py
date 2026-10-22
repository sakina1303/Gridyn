"""Small, auditable fixtures for ingestion, quality and claim gates."""

import unittest
from datetime import datetime, timedelta, timezone

from energy_lab.core.assets import BatteryConfig, GridConfig, PVConfig, SiteConfig
from energy_lab.core.time import make_intervals
from energy_lab.data.ingest import DataIngestionError, ingest_csv_text
from energy_lab.data.quality import assess_quality
from energy_lab.data.readiness import assess_readiness
from energy_lab.simulation.observer import ObservedRecord


START = datetime(2026, 1, 1, tzinfo=timezone.utc)


class DataReadinessTests(unittest.TestCase):
    def test_csv_energy_to_average_power_and_hash(self):
        csv = "start,end,quantity,value,unit\n2026-01-01T00:00:00Z,2026-01-01T00:15:00Z,grid_import_kw,2.5,kWh\n"
        first = ingest_csv_text(csv, dataset_id="meter-1", site_timezone="Asia/Kolkata")
        second = ingest_csv_text(csv, dataset_id="meter-1", site_timezone="Asia/Kolkata")
        self.assertEqual(first.records[0].value, 10)
        self.assertEqual(first.records[0].unit, "kW")
        self.assertEqual(first.normalized_sha256, second.normalized_sha256)

    def test_csv_rejects_unknown_units_and_ambiguous_local_time(self):
        bad_unit = "start,end,quantity,value,unit\n2026-01-01T00:00:00Z,2026-01-01T00:15:00Z,grid_import_kw,1,apples\n"
        with self.assertRaises(DataIngestionError):
            ingest_csv_text(bad_unit, dataset_id="bad", site_timezone="Asia/Kolkata")
        ambiguous = "start,end,quantity,value,unit\n2026-11-01T01:00:00,2026-11-01T01:15:00,grid_import_kw,1,kW\n"
        with self.assertRaises(DataIngestionError):
            ingest_csv_text(ambiguous, dataset_id="dst", site_timezone="America/New_York")

    def test_quality_injected_faults_are_explicit(self):
        intervals = make_intervals(START, 8, 15)
        records = [ObservedRecord(t, "grid_import_kw", 10, "kW") for t in intervals if t != intervals[3]]
        records.append(records[0])
        records.append(ObservedRecord(intervals[4], "pv_available_kw", 100, "kW"))
        records.append(ObservedRecord(intervals[5], "fixed_load_kw", -1, "kW"))
        report = assess_quality(tuple(records), expected_start_utc=START,
                                expected_end_utc=START + timedelta(hours=2),
                                declared_resolution_minutes=15, site_timezone="Asia/Kolkata",
                                site_rating_kw=50, pv_capacity_kw=10)
        codes = {issue.code for issue in report.issues}
        self.assertTrue({"duplicate", "missing_intervals", "pv_above_capacity", "negative_gross_value"} <= codes)
        self.assertEqual(report.for_quantity("grid_import_kw").coverage, 7 / 8)
        self.assertEqual(report.for_quantity("grid_import_kw").status, "invalid")

    def test_quality_detects_sustained_cross_signal_imbalance(self):
        intervals = make_intervals(START, 4, 15)
        values = {"pv_used_kw": 0, "grid_import_kw": 20, "grid_export_kw": 0,
                  "battery_charge_kw": 0, "battery_discharge_kw": 0,
                  "critical_load_kw": 5, "fixed_load_kw": 5, "flexible_load_kw": 0}
        records = tuple(ObservedRecord(t, q, value, "kW") for t in intervals for q, value in values.items())
        report = assess_quality(records, expected_start_utc=START, expected_end_utc=START + timedelta(hours=1),
                                declared_resolution_minutes=15, site_timezone="Asia/Kolkata", site_rating_kw=50)
        self.assertIn("cross_signal_imbalance", {issue.code for issue in report.issues})

    def test_readiness_keeps_synthetic_and_missing_tariff_claims_limited(self):
        intervals = make_intervals(START, 4, 15)
        records = tuple(ObservedRecord(t, "grid_import_kw", 10, "kW") for t in intervals)
        quality = assess_quality(records, expected_start_utc=START, expected_end_utc=START + timedelta(hours=1),
                                 declared_resolution_minutes=15, site_timezone="Asia/Kolkata", site_rating_kw=50)
        site = SiteConfig("s", "Asia/Kolkata", GridConfig(50, 0), PVConfig(5),
                          BatteryConfig(20, 0.1, 0.9, 10, 5, 5, 0.9, 0.9))
        observed = assess_readiness(quality, site, evidence_kind="observed")
        synthetic = assess_readiness(quality, site, evidence_kind="synthetic")
        self.assertEqual(observed.for_claim("measured_15min_peak").state, "usable")
        self.assertEqual(synthetic.for_claim("measured_15min_peak").state, "insufficient")
        self.assertEqual(observed.for_claim("applicable_tariff_cost").state, "insufficient")
        self.assertEqual(observed.for_claim("firm_battery_response").state, "usable_with_limitations")


if __name__ == "__main__":
    unittest.main()
