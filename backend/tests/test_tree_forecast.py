"""Tree comparator trains only before its decision issue time."""

import unittest
from datetime import datetime, timezone

from energy_lab.core.time import make_intervals
from energy_lab.forecasting.tree import issue_tree_forecast
from energy_lab.simulation.observer import ObservedRecord


class TreeForecastTests(unittest.TestCase):
    def test_future_records_do_not_change_prediction(self):
        intervals = make_intervals(datetime(2026, 1, 1, tzinfo=timezone.utc), 9 * 96, 15)
        records = tuple(ObservedRecord(item, "fixed_load_kw", float(10 + index % 96), "kW")
                        for index, item in enumerate(intervals))
        issue = intervals[8 * 96].start
        future = intervals[8 * 96:8 * 96 + 4]
        first = issue_tree_forecast(records, target="fixed_load_kw", issue_at_utc=issue,
                                    intervals=future, site_timezone="Asia/Kolkata", seed=7)
        changed = records[:8 * 96] + tuple(ObservedRecord(item.interval, item.quantity, 999, item.unit)
                                            for item in records[8 * 96:])
        second = issue_tree_forecast(changed, target="fixed_load_kw", issue_at_utc=issue,
                                     intervals=future, site_timezone="Asia/Kolkata", seed=7)
        self.assertEqual(first.values_kw, second.values_kw)
        self.assertEqual(first.training_end_utc, issue)
        self.assertEqual(first.training_count, 8 * 96)


if __name__ == "__main__":
    unittest.main()
