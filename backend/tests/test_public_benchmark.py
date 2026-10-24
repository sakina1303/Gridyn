"""Hand-checkable observed-meter aggregation and issue-time stress fixtures."""

import unittest
from datetime import datetime, timedelta, timezone

from energy_lab.core.time import make_intervals
from energy_lab.data.ingest import ingest_csv_text
from energy_lab.experiments.public_benchmark import (
    TARGET, aggregate_minutes, conditions, evaluate_observed_forecasts, perturb_training,
)
from energy_lab.simulation.observer import ObservedRecord


START = datetime(2026, 1, 1, tzinfo=timezone.utc)


class PublicBenchmarkTests(unittest.TestCase):
    def test_complete_minute_block_becomes_average_kw_and_partial_block_abstains(self):
        base = int(START.timestamp())
        rows = [(str(base + minute * 60), str(1000 + 100 * minute)) for minute in range(15)]
        rows += [(str(base + 900 + minute * 60), "2000") for minute in range(14)]
        rows += [("1.377e+09", "5000"), (str(base), "1000")]
        result = aggregate_minutes(rows, start_utc=START, end_utc=START + timedelta(minutes=30))
        self.assertEqual(result.complete_intervals, 1)
        self.assertEqual(result.records[0].value, 1.7)
        self.assertEqual(result.missing_or_partial_intervals, 1)
        self.assertEqual(result.invalid_source_rows, 1)
        self.assertEqual(result.duplicate_source_minutes, 1)

    def test_metered_building_load_import_does_not_become_grid_import(self):
        source = "start,end,quantity,value,unit\n2026-01-01T00:00:00Z,2026-01-01T00:15:00Z,metered_building_load_kw,1500,W\n"
        imported = ingest_csv_text(source, dataset_id="public", site_timezone="Asia/Kolkata")
        self.assertEqual(imported.records[0].quantity, TARGET)
        self.assertEqual(imported.records[0].value, 1.5)

    def test_future_meter_changes_cannot_change_training_or_issued_forecast(self):
        intervals = make_intervals(START, 3 * 96, 15)
        records = tuple(ObservedRecord(item, TARGET, float(10 + index % 96), "kW")
                        for index, item in enumerate(intervals))
        issue = intervals[96].start
        changed_future = records[:96] + tuple(
            ObservedRecord(item.interval, TARGET, 999, "kW") for item in records[96:])
        condition = conditions()[0]
        first = perturb_training(records, issue_at_utc=issue, condition=condition, seed=7)
        second = perturb_training(changed_future, issue_at_utc=issue, condition=condition, seed=7)
        self.assertEqual(first, second)
        study = evaluate_observed_forecasts(records, issue_times_utc=(issue,))
        self.assertEqual(study["provenance"], "observed building mains + injected synthetic sensor stress")
        self.assertTrue(any(item["status"] == "abstained" for item in study["folds"]))
        self.assertTrue(any(item["status"] == "evaluated" for item in study["folds"]))


if __name__ == "__main__":
    unittest.main()
