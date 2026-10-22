"""Seven-step local synthetic research demo through the same HTTP contracts."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from energy_lab.api.app import create_app


def main() -> None:
    client = TestClient(create_app(Path(".local/demo.sqlite3")))
    site = client.post("/v1/sites", json={
        "name": "Synthetic research campus", "timezone": "Asia/Kolkata",
        "grid": {"import_limit_kw": 250, "export_limit_kw": 40},
        "pv": {"ac_capacity_kw": 80},
        "battery": {"nominal_capacity_kwh": 100, "min_soc_fraction": 0.1,
                    "max_soc_fraction": 0.9, "initial_energy_kwh": 50,
                    "max_charge_kw": 25, "max_discharge_kw": 25,
                    "charge_efficiency": 0.9, "discharge_efficiency": 0.9},
    }).json()
    site_id = site["site_id"]
    dataset = client.post(f"/v1/sites/{site_id}/synthetic-datasets", json={
        "start_utc": "2026-01-01T00:00:00Z", "interval_count": 192, "seed": 7}).json()
    dataset_id = dataset["dataset_id"]
    readiness = client.post(f"/v1/datasets/{dataset_id}/validate", json={}).json()
    assessment = client.post(f"/v1/sites/{site_id}/flexibility-assessments", json={
        "dataset_id": dataset_id, "start_index": 96, "duration_intervals": 4,
        "direction": "down", "seed": 7}).json()
    optimization = client.post(f"/v1/sites/{site_id}/optimization-runs", json={
        "dataset_id": dataset_id, "objective_profile": "peak", "seed": 7}).json()
    run_id = optimization["run_id"]
    recommendation = client.get(f"/v1/recommendations?run_id={run_id}").json()
    report = client.get(f"/v1/reports/{run_id}?format=markdown").text
    output = Path(".local/demo-report.md")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(report, encoding="utf-8")
    print("SIMULATION DATA ONLY")
    print("1 Site:", site_id)
    print("2 Truth checksum:", dataset["truth_sha256"])
    print("3 Measured peak claim:", readiness["readiness"]["measured_15min_peak"])
    print("4 Envelope:", assessment["status"], assessment["run_id"])
    print("5 Optimizer:", optimization["status"], optimization["objective_value"], optimization["objective_unit"])
    print("6 Recommendation:", recommendation["status"], "reliability:", recommendation.get("reliability", "unknown"))
    print("7 Report:", output)


if __name__ == "__main__":
    main()
