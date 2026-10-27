"""Typed local API path from site setup to validated research report."""

import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from energy_lab.api.app import create_app


class APITests(unittest.TestCase):
    def test_uncertainty_matrix_exposes_evidence_and_unknown_claims(self):
        with tempfile.TemporaryDirectory() as directory:
            client = TestClient(create_app(Path(directory) / "lab.sqlite3"))
            response = client.get("/v1/uncertainty-matrix")
            self.assertEqual(response.status_code, 200, response.text)
            body = response.json()
            self.assertEqual(body["synthetic_physical"]["row_count"], 792)
            self.assertEqual(body["paired_observation"]["variant_count"], 13)
            self.assertEqual(body["public_observed_load"]["target"], "metered_building_load_kw")
            self.assertEqual(body["claim_status"]["field_flexibility_reliability"], "unknown")

    def test_public_benchmark_is_observed_load_only(self):
        with tempfile.TemporaryDirectory() as directory:
            client = TestClient(create_app(Path(directory) / "lab.sqlite3"))
            response = client.get("/v1/public-benchmarks/iblend-academic")
            self.assertEqual(response.status_code, 200, response.text)
            body = response.json()
            self.assertEqual(body["source"]["license"], "CC0")
            self.assertEqual(body["aggregation"]["complete_intervals"], 3927)
            self.assertEqual(body["target"], "metered_building_load_kw")
            self.assertIn("No site-wide import", body["limitations"][0])

    def test_forecast_decision_study_records_short_history_and_report(self):
        with tempfile.TemporaryDirectory() as directory:
            client = TestClient(create_app(Path(directory) / "lab.sqlite3"))
            site = client.post("/v1/sites", json={
                "name": "Synthetic forecast test", "timezone": "Asia/Kolkata",
                "grid": {"import_limit_kw": 250, "export_limit_kw": 0},
                "pv": {"ac_capacity_kw": 0}}).json()
            site_id = site["site_id"]
            dataset = client.post(f"/v1/sites/{site_id}/synthetic-datasets", json={
                "start_utc": "2026-01-01T00:00:00Z", "interval_count": 192}).json()
            dataset_id = dataset["dataset_id"]
            study = client.post(f"/v1/sites/{site_id}/forecast-decision-studies", json={
                "dataset_id": dataset_id, "issue_index": 96, "horizon_intervals": 4})
            self.assertEqual(study.status_code, 201, study.text)
            body = study.json()
            self.assertEqual(body["truth_sha256"], dataset["truth_sha256"])
            self.assertEqual([item["method"] for item in body["methods"]],
                             ["previous_day", "random_forest"])
            self.assertIsNotNone(body["methods"][0]["forecast_mae_kw"])
            self.assertIsNotNone(body["methods"][0]["realized_objective"])
            self.assertEqual(body["methods"][1]["solver_status"], "unavailable")
            self.assertIn("seven", body["methods"][1]["failure_reason"])
            self.assertEqual(body["reliability"], "unknown")
            report = client.get(f"/v1/reports/{body['run_id']}")
            self.assertEqual(report.status_code, 200, report.text)
            self.assertEqual(report.json()["sections"]["forecast_and_uncertainty"]["methods"], body["methods"])
            self.assertIn("Forecast decision study", client.get(
                f"/v1/reports/{body['run_id']}?format=markdown").text)
            outside = client.post(f"/v1/sites/{site_id}/forecast-decision-studies", json={
                "dataset_id": dataset_id, "issue_index": 192, "horizon_intervals": 1})
            self.assertEqual(outside.status_code, 422)
            self.assertEqual(outside.json()["detail"]["code"], "invalid_horizon")

    def test_forecast_decision_study_can_evaluate_tree_with_seven_day_history(self):
        with tempfile.TemporaryDirectory() as directory:
            client = TestClient(create_app(Path(directory) / "lab.sqlite3"))
            site_id = client.post("/v1/sites", json={
                "name": "Synthetic long history", "timezone": "Asia/Kolkata",
                "grid": {"import_limit_kw": 250, "export_limit_kw": 0},
                "pv": {"ac_capacity_kw": 0}}).json()["site_id"]
            dataset = client.post(f"/v1/sites/{site_id}/synthetic-datasets", json={
                "start_utc": "2026-01-01T00:00:00Z", "interval_count": 8 * 96})
            self.assertEqual(dataset.status_code, 201, dataset.text)
            study = client.post(f"/v1/sites/{site_id}/forecast-decision-studies", json={
                "dataset_id": dataset.json()["dataset_id"],
                "issue_index": 7 * 96, "horizon_intervals": 4})
            self.assertEqual(study.status_code, 201, study.text)
            outcomes = study.json()["methods"]
            self.assertTrue(all(item["training_end_utc"] == study.json()["issue_at_utc"]
                                for item in outcomes))
            self.assertTrue(all(item["forecast_mae_kw"] is not None for item in outcomes))

    def test_synthetic_setup_readiness_assessment_optimizer_report(self):
        with tempfile.TemporaryDirectory() as directory:
            client = TestClient(create_app(Path(directory) / "lab.sqlite3"))
            site = client.post("/v1/sites", json={
                "name": "Synthetic campus", "timezone": "Asia/Kolkata",
                "grid": {"import_limit_kw": 100, "export_limit_kw": 0},
                "pv": {"ac_capacity_kw": 0},
                "battery": {"nominal_capacity_kwh": 20, "min_soc_fraction": 0.1,
                            "max_soc_fraction": 0.9, "initial_energy_kwh": 10,
                            "max_charge_kw": 5, "max_discharge_kw": 5,
                            "charge_efficiency": 1, "discharge_efficiency": 1},
            })
            self.assertEqual(site.status_code, 201, site.text)
            site_id = site.json()["site_id"]
            dataset = client.post(f"/v1/sites/{site_id}/synthetic-datasets", json={
                "start_utc": "2026-01-01T00:00:00Z", "interval_count": 4,
                "critical_base_kw": 5, "fixed_base_kw": 5,
                "day_activity_kw": 0, "evening_activity_kw": 0,
                "cooling_kw_per_c_above_28": 0,
            })
            self.assertEqual(dataset.status_code, 201, dataset.text)
            dataset_id = dataset.json()["dataset_id"]
            readiness = client.post(f"/v1/datasets/{dataset_id}/validate", json={})
            self.assertEqual(readiness.status_code, 200, readiness.text)
            self.assertEqual(readiness.json()["readiness"]["measured_15min_peak"], "insufficient")
            assessment = client.post(f"/v1/sites/{site_id}/flexibility-assessments", json={
                "dataset_id": dataset_id, "start_index": 0, "duration_intervals": 1,
                "direction": "down"})
            self.assertEqual(assessment.status_code, 201, assessment.text)
            self.assertEqual(assessment.json()["status"], "succeeded")
            self.assertIsNone(client.get(f"/v1/runs/{assessment.json()['run_id']}").json()["reliable_kw"])
            decision = client.get(f"/v1/runs/{assessment.json()['run_id']}/decision-brief")
            self.assertEqual(decision.status_code, 200, decision.text)
            self.assertEqual(decision.json()["status"], "simulation_only")
            self.assertEqual(decision.json()["operational_use"], "do_not_dispatch")
            self.assertIsNone(decision.json()["field_reliability"])
            self.assertEqual(decision.json()["response"]["duration_hours"], .25)
            sensitivity = client.get(
                f"/v1/runs/{assessment.json()['run_id']}/measurement-sensitivity")
            self.assertEqual(sensitivity.status_code, 200, sensitivity.text)
            self.assertTrue(sensitivity.json()["synthetic"])
            self.assertEqual(sensitivity.json()["source_run_id"], assessment.json()["run_id"])
            self.assertIn("field priority unvalidated", sensitivity.json()["result"]["limitation"])
            assessment_report = client.get(
                f"/v1/reports/{assessment.json()['run_id']}?format=json")
            self.assertEqual(assessment_report.status_code, 200, assessment_report.text)
            self.assertEqual(assessment_report.json()["sections"]["measurement_sensitivity"]["source_run_id"],
                             assessment.json()["run_id"])
            self.assertIn("Synthetic model sensitivity",
                          client.get(f"/v1/reports/{assessment.json()['run_id']}?format=markdown").text)
            optimized = client.post(f"/v1/sites/{site_id}/optimization-runs", json={
                "dataset_id": dataset_id, "objective_profile": "peak"})
            self.assertEqual(optimized.status_code, 201, optimized.text)
            self.assertEqual(optimized.json()["status"], "succeeded")
            run_id = optimized.json()["run_id"]
            self.assertEqual(client.get(f"/v1/runs/{run_id}/measurement-sensitivity").status_code, 409)
            report = client.get(f"/v1/reports/{run_id}?format=markdown")
            self.assertIn("SIMULATION DATA ONLY", report.text)
            self.assertIn("Validated metrics", report.text)
            report_json = client.get(f"/v1/reports/{run_id}?format=json").json()
            self.assertEqual(report_json["dataset_id"], dataset_id)
            self.assertTrue(report_json["metrics"])
            self.assertTrue(all(item["run_id"] == run_id and item["dataset_sha256"] == dataset.json()["truth_sha256"]
                                for item in report_json["metrics"]))
            recommendation = client.get(f"/v1/recommendations?run_id={run_id}")
            self.assertEqual(recommendation.status_code, 200)
            scenario = client.post(f"/v1/sites/{site_id}/scenarios", json={"dataset_id": dataset_id,
                "grid_import_limit_kw": 50})
            self.assertEqual(scenario.status_code, 201, scenario.text)
            compared = client.post(f"/v1/sites/{site_id}/scenarios/{scenario.json()['scenario_id']}/compare")
            self.assertEqual(compared.status_code, 201, compared.text)
            self.assertEqual(compared.json()["outcome"]["truth_sha256"], dataset.json()["truth_sha256"])
            self.assertEqual(compared.json()["outcome"]["rule_status"], "valid")
            self.assertIsNotNone(compared.json()["outcome"]["rule_peak_kw"])
            stress = client.post(
                f"/v1/sites/{site_id}/scenarios/{scenario.json()['scenario_id']}/stress-aware-compare")
            self.assertEqual(stress.status_code, 201, stress.text)
            self.assertTrue(stress.json()["synthetic"])
            self.assertIn("statistical reliability unknown", stress.json()["outcome"]["evidence_label"])
            self.assertTrue(stress.json()["evaluation_stresses"])
            if stress.json()["outcome"]["status"] == "selected":
                self.assertEqual(len(stress.json()["schedule"]), 4)
                stress_report = client.get(f"/v1/reports/{stress.json()['run_id']}?format=markdown")
                self.assertEqual(stress_report.status_code, 200, stress_report.text)
                self.assertIn("Declared synthetic stress study", stress_report.text)
            if Path("frontend/dist/index.html").exists():
                self.assertIn("FlexGrid", client.get("/").text)
            self.assertFalse(any("control" in route.path for route in create_app(Path(directory) / "other.sqlite3").routes))

    def test_invalid_units_and_missing_resource_have_typed_errors(self):
        with tempfile.TemporaryDirectory() as directory:
            client = TestClient(create_app(Path(directory) / "lab.sqlite3"))
            response = client.post("/v1/sites", json={"name": "bad", "timezone": "Asia/Kolkata",
                "grid": {"import_limit_kw": -1, "export_limit_kw": 0}, "pv": {"ac_capacity_kw": 0}})
            self.assertEqual(response.status_code, 422)
            self.assertEqual(response.json()["code"], "invalid_request")
            missing = client.get("/v1/runs/no-such-run")
            self.assertEqual(missing.status_code, 404)
            self.assertEqual(missing.json()["detail"]["code"], "not_found")

    def test_observed_csv_peak_claim_and_invalid_unit(self):
        with tempfile.TemporaryDirectory() as directory:
            client = TestClient(create_app(Path(directory) / "lab.sqlite3"))
            site_id = client.post("/v1/sites", json={"name": "meter test", "timezone": "Asia/Kolkata",
                "grid": {"import_limit_kw": 50, "export_limit_kw": 0},
                "pv": {"ac_capacity_kw": 0}}).json()["site_id"]
            csv = ("start,end,quantity,value,unit\n"
                   "2026-01-01T00:00:00Z,2026-01-01T00:15:00Z,grid_import_kw,2.5,kWh\n"
                   "2026-01-01T00:15:00Z,2026-01-01T00:30:00Z,grid_import_kw,3,kWh\n")
            uploaded = client.post(f"/v1/sites/{site_id}/datasets",
                data={"interval_minutes": "15", "source": "test meter"},
                files={"file": ("meter.csv", csv, "text/csv")})
            self.assertEqual(uploaded.status_code, 201, uploaded.text)
            dataset_id = uploaded.json()["dataset_id"]
            quality = client.post(f"/v1/datasets/{dataset_id}/validate", json={}).json()
            self.assertEqual(quality["readiness"]["measured_15min_peak"], "usable")
            observations = client.get(f"/v1/datasets/{dataset_id}/observations").json()["records"]
            self.assertEqual([item["value"] for item in observations], [10, 12])
            bad = client.post(f"/v1/sites/{site_id}/datasets", data={"interval_minutes": "15"},
                files={"file": ("bad.csv", csv.replace("kWh", "bananas"), "text/csv")})
            self.assertEqual(bad.status_code, 422)
            self.assertEqual(bad.json()["detail"]["code"], "invalid_dataset")

    def test_api_accepts_ev_pump_hvac_and_replays_joint_schedule(self):
        with tempfile.TemporaryDirectory() as directory:
            client = TestClient(create_app(Path(directory) / "lab.sqlite3"))
            window = {"start": "2026-01-01T05:00:00Z", "end": "2026-01-01T12:00:00Z"}
            site_response = client.post("/v1/sites", json={"name": "multi-asset", "timezone": "Asia/Kolkata",
                "grid": {"import_limit_kw": 250, "export_limit_kw": 0}, "pv": {"ac_capacity_kw": 0},
                "evs": [{"asset_id": "ev", "window": window, "required_energy_kwh": 10,
                         "max_power_kw": 10}],
                "pumps": [{"asset_id": "pump", "window": window, "rated_power_kw": 3,
                           "required_runtime_hours": 1, "minimum_run_intervals": 2}],
                "hvacs": [{"asset_id": "hvac", "windows": [window], "min_power_kw": 2,
                           "max_power_kw": 5}]})
            self.assertEqual(site_response.status_code, 201, site_response.text)
            site_id = site_response.json()["site_id"]
            dataset = client.post(f"/v1/sites/{site_id}/synthetic-datasets", json={
                "start_utc": "2026-01-01T00:00:00Z", "interval_count": 96}).json()
            optimized = client.post(f"/v1/sites/{site_id}/optimization-runs", json={
                "dataset_id": dataset["dataset_id"], "objective_profile": "peak"})
            self.assertEqual(optimized.status_code, 201, optimized.text)
            self.assertEqual(optimized.json()["status"], "succeeded", optimized.text)


if __name__ == "__main__":
    unittest.main()
