"""Observed paired-series forecasts use only prior intervals and retain abstentions."""

import unittest

from energy_lab.experiments.paired_public_data import INTERVALS_PER_DAY, evaluate_paired_series


class PairedPublicDataTests(unittest.TestCase):
    def test_previous_day_and_week_use_prior_slots(self):
        count = 9 * INTERVALS_PER_DAY
        load = tuple(float(index // INTERVALS_PER_DAY) for index in range(count))
        pv = tuple(float(index % INTERVALS_PER_DAY) for index in range(count))
        result = evaluate_paired_series({"consumer_load_kw": load, "pv_output_kw": pv},
                                        first_test_day=7, test_days=2)
        load_rows = [item for item in result["folds"] if item["signal"] == "consumer_load_kw"]
        day = next(item for item in load_rows if item["test_day_index"] == 7
                   and item["method"] == "previous_day")
        week = next(item for item in load_rows if item["test_day_index"] == 7
                    and item["method"] == "previous_week")
        self.assertEqual(day["mae_kw"], 1)
        self.assertEqual(week["mae_kw"], 7)
        self.assertEqual(day["evaluated_intervals"], INTERVALS_PER_DAY)
        self.assertTrue(all(item["mae_kw"] == 0 for item in result["folds"]
                            if item["signal"] == "pv_output_kw"))

    def test_missing_training_or_test_slot_abstains_without_fill(self):
        count = 8 * INTERVALS_PER_DAY
        load = [2.0] * count
        pv = [1.0] * count
        load[6 * INTERVALS_PER_DAY] = None  # prior day only
        pv[7 * INTERVALS_PER_DAY] = None  # held-out day
        result = evaluate_paired_series({"consumer_load_kw": tuple(load), "pv_output_kw": tuple(pv)},
                                        first_test_day=7, test_days=1)
        self.assertEqual(next(row for row in result["folds"] if row["signal"] == "consumer_load_kw"
                              and row["method"] == "previous_day")["status"], "abstained")
        self.assertTrue(all(row["status"] == "abstained" for row in result["folds"]
                            if row["signal"] == "pv_output_kw"))

    def test_future_change_cannot_change_prior_day_prediction(self):
        count = 8 * INTERVALS_PER_DAY
        base = {"consumer_load_kw": (2.0,) * count, "pv_output_kw": (1.0,) * count}
        changed = {**base, "consumer_load_kw": base["consumer_load_kw"][:7 * INTERVALS_PER_DAY]
                   + (9.0,) * INTERVALS_PER_DAY}
        original = evaluate_paired_series(base, first_test_day=7, test_days=1)
        later = evaluate_paired_series(changed, first_test_day=7, test_days=1)
        # Past values are fixed; the changed held-out day raises observed error.
        original_row = next(row for row in original["folds"] if row["signal"] == "consumer_load_kw"
                            and row["method"] == "previous_day")
        later_row = next(row for row in later["folds"] if row["signal"] == "consumer_load_kw"
                         and row["method"] == "previous_day")
        self.assertEqual(original_row["mae_kw"], 0)
        self.assertEqual(later_row["mae_kw"], 7)

    def test_daylight_window_retains_missing_data_abstention(self):
        count = 8 * INTERVALS_PER_DAY
        load = (2.0,) * count
        pv = [None] * count
        for day in (0, 6, 7):
            for slot in range(40, 60):
                pv[day * INTERVALS_PER_DAY + slot] = 1.0
        result = evaluate_paired_series({"building_load_kw": load, "pv_output_kw": tuple(pv)},
                                        first_test_day=7, test_days=1,
                                        evaluation_windows={"pv_output_kw": (40, 60)})
        pv_rows = [row for row in result["folds"] if row["signal"] == "pv_output_kw"]
        self.assertTrue(all(row["status"] == "evaluated" and row["evaluated_intervals"] == 20
                            for row in pv_rows))
        pv[7 * INTERVALS_PER_DAY + 45] = None
        changed = evaluate_paired_series({"building_load_kw": load, "pv_output_kw": tuple(pv)},
                                         first_test_day=7, test_days=1,
                                         evaluation_windows={"pv_output_kw": (40, 60)})
        self.assertTrue(all(row["status"] == "abstained" for row in changed["folds"]
                            if row["signal"] == "pv_output_kw"))


if __name__ == "__main__":
    unittest.main()
