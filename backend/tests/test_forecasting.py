"""Issue-time contract and hand-computable rolling forecast metrics."""

import unittest
from datetime import datetime, timezone

from energy_lab.core.time import make_intervals
from energy_lab.forecasting.backtest import rolling_backtest
from energy_lab.forecasting.baseline import issue_forecast
from energy_lab.simulation.observer import ObservedRecord


class ForecastTests(unittest.TestCase):
    def setUp(self):
        self.intervals = make_intervals(datetime(2026, 1, 1, tzinfo=timezone.utc), 192, 15)
        self.observed = tuple(ObservedRecord(interval, "fixed_load_kw", float(index % 96), "kW")
                              for index, interval in enumerate(self.intervals))
        self.issue = self.intervals[96].start

    def test_previous_day_forecast_and_heldout_error(self):
        future = self.intervals[96:100]
        forecast = issue_forecast(self.observed, target="fixed_load_kw", method="previous_day",
                                  issue_at_utc=self.issue, intervals=future, site_timezone="Asia/Kolkata")
        self.assertEqual(forecast.values_kw, (0, 1, 2, 3))
        self.assertEqual(forecast.training_end_utc, self.issue)
        truth = tuple(ObservedRecord(interval, "fixed_load_kw", float(index % 96) + (2 if index >= 96 else 0), "kW")
                      for index, interval in enumerate(self.intervals))
        result = rolling_backtest(self.observed, truth, target="fixed_load_kw", method="previous_day",
                                  issue_times_utc=(self.issue,), horizon_intervals=4, site_timezone="Asia/Kolkata")
        self.assertEqual(result.mae_kw, 2)
        self.assertEqual(result.rmse_kw, 2)

    def test_future_observations_cannot_change_issued_forecast(self):
        future = self.intervals[96:100]
        modified = self.observed[:96] + tuple(ObservedRecord(record.interval, record.quantity, 999, record.unit)
                                              for record in self.observed[96:])
        for method in ("previous_day", "hour_day_mean", "calendar_ridge"):
            first = issue_forecast(self.observed, target="fixed_load_kw", method=method,
                                   issue_at_utc=self.issue, intervals=future, site_timezone="Asia/Kolkata")
            second = issue_forecast(modified, target="fixed_load_kw", method=method,
                                    issue_at_utc=self.issue, intervals=future, site_timezone="Asia/Kolkata")
            self.assertEqual(first.values_kw, second.values_kw)
            self.assertEqual(first.training_count, 96)

    def test_missing_lag_and_duplicate_training_are_rejected(self):
        with self.assertRaises(ValueError):
            issue_forecast(self.observed[1:96], target="fixed_load_kw", method="previous_day",
                           issue_at_utc=self.issue, intervals=self.intervals[96:97], site_timezone="Asia/Kolkata")
        with self.assertRaises(ValueError):
            issue_forecast(self.observed[:96] + self.observed[:1], target="fixed_load_kw", method="calendar_ridge",
                           issue_at_utc=self.issue, intervals=self.intervals[96:97], site_timezone="Asia/Kolkata")


if __name__ == "__main__":
    unittest.main()
