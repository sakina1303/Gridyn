"""Decision briefs must preserve the synthetic and field evidence boundary."""

import unittest

from energy_lab.advisory.decision import build_decision_brief
from energy_lab.core.assets import BatteryConfig, GridConfig, PVConfig, SiteConfig


class DecisionBriefTests(unittest.TestCase):
    def setUp(self):
        self.site = SiteConfig("campus", "Asia/Kolkata", GridConfig(100, 0), PVConfig(20),
                               BatteryConfig(20, .1, .9, 10, 5, 5, 1, 1))
        self.run = {"run_id": "r1", "dataset_id": "d1", "kind": "flexibility_assessment",
                    "synthetic": True, "status": "succeeded", "direction": "down",
                    "duration_intervals": 4, "recovery_import_delta_kwh": 2,
                    "passes": [{"mode": "operational", "status": "optimal", "sustained_kw": 3}]}

    def test_validated_synthetic_response_is_never_a_field_promise(self):
        brief = build_decision_brief(self.run, self.site)
        self.assertEqual(brief["response"]["sustained_kw"], 3)
        self.assertEqual(brief["response"]["duration_hours"], 1)
        self.assertEqual(brief["status"], "simulation_only")
        self.assertEqual(brief["operational_use"], "do_not_dispatch")
        self.assertIsNone(brief["field_reliability"])
        self.assertIsNone(brief["binding_constraint"])
        self.assertEqual({item["signal"] for item in brief["next_measurements"]},
                         {"Site grid import", "Solar PV", "Battery"})

    def test_failed_assessment_does_not_publish_response(self):
        run = {**self.run, "status": "infeasible", "reason": "grid limit",
               "passes": [{"mode": "operational", "status": "infeasible", "sustained_kw": None}]}
        brief = build_decision_brief(run, self.site)
        self.assertEqual(brief["status"], "no_validated_response")
        self.assertIsNone(brief["response"]["sustained_kw"])
        self.assertEqual(brief["failure_reason"], "grid limit")

    def test_zero_kw_is_not_presented_as_a_response(self):
        run = {**self.run, "passes": [{"mode": "operational", "status": "optimal", "sustained_kw": 0}]}
        brief = build_decision_brief(run, self.site)
        self.assertEqual(brief["status"], "no_validated_response")
        self.assertIsNone(brief["response"]["sustained_kw"])


if __name__ == "__main__":
    unittest.main()
