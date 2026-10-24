"""Physical and evidence-boundary checks for the declared uncertainty matrix."""

import unittest

from energy_lab.core.units import balance_tolerance_kw
from energy_lab.experiments.synthetic_matrix import run_synthetic_matrix


class SyntheticMatrixTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.study = run_synthetic_matrix()
        cls.rows = cls.study["rows"]

    def test_all_durations_directions_and_seeds_have_clean_delivery(self):
        clean = [row for row in self.rows if row["factor"] == "control"]
        self.assertEqual(len(clean), 18)
        self.assertEqual({row["status"] for row in clean}, {"delivered"})
        self.assertEqual({row["response_duration_hours"] for row in clean}, {1, 2, 4})
        self.assertEqual({row["direction"] for row in clean}, {"up", "down"})
        tolerance = balance_tolerance_kw(24)
        self.assertTrue(all(row["physical_balance_max_abs_kw"] <= tolerance for row in clean))
        self.assertTrue(all(row["overstatement_kw"] <= tolerance for row in clean))

    def test_physical_failures_and_unavailable_claims_are_not_dropped(self):
        self.assertEqual(len(self.rows), 792)
        self.assertTrue(any(row["factor"] == "PV truth deviation" and
                            row["status"] == "candidate_infeasible" for row in self.rows))
        self.assertTrue(any(row["factor"] == "initial battery SOC" and
                            row["status"] == "candidate_infeasible" for row in self.rows))
        self.assertTrue(any(row["factor"] == "high initial battery SOC" and
                            row["direction"] == "up" and row["status"] == "candidate_infeasible"
                            for row in self.rows))
        self.assertTrue(any(row["factor"] == "EV departure" and
                            row["status"] == "candidate_infeasible" for row in self.rows))
        self.assertTrue(any(row["factor"] == "battery discharge rating" and
                            row["status"] == "candidate_infeasible" for row in self.rows))
        self.assertTrue(any(row["factor"] == "load magnitude" and
                            row["status"] == "overstated" and row["overstatement_kw"] > 0
                            for row in self.rows))
        self.assertTrue(all(row["physical_balance_max_abs_kw"] <= balance_tolerance_kw(24)
                            for row in self.rows if row["status"] in {"delivered", "overstated"}))
        for row in self.rows:
            if row["status"] in {"baseline_infeasible", "candidate_infeasible", "not_evaluable"}:
                self.assertIsNone(row["delivered_sustained_kw"])
                self.assertIsNotNone(row["reason"])

    def test_comfort_and_tariff_claims_remain_unevaluable(self):
        unavailable = [row for row in self.rows if row["factor"] in
                       {"outdoor temperature", "tariff and EV interaction"}]
        self.assertEqual(len(unavailable), 72)
        self.assertEqual({row["status"] for row in unavailable}, {"not_evaluable"})
        self.assertIn("field reliability unknown", self.study["evidence_label"])

    def test_same_seed_reproduces_rows(self):
        first = run_synthetic_matrix(seeds=(7,))
        second = run_synthetic_matrix(seeds=(7,))
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
